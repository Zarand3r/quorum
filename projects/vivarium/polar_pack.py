"""Polarity that EMERGES from the morphing contour blob — as a FAITHFUL attention head.

The grounded-contour tokens of `pack.py` start spherical and MORPH into pronged shapes (K=3 → up to
three protrusions). A protrusion is a POSITIVE charge, the body/centre is NEGATIVE — so the blob becomes
polar *because it deformed* (this is the same spikiness the viewer already colours by). The electrostatic
interaction is added as ONE bounded, bearing-aware attention head — NOT a Coulomb `1/d²` force kernel
(design/HARD_REQUIREMENT.md forbids that). It is transformer-only:

    near-face charge i presents toward j:  nf_i(j) = ⟨C_i, basis(θ_{i→j})⟩          (grounded readout of
        the contour at the relative BEARING to j — a RoPE-style relative-position attention term; a prong
        facing j → nf>0, a valley/centre facing j → nf<0)
    electrostatic pair term:               prod = nf_i(j)·nf_j(i)                    (>0 like faces, <0 opp.)
    bounded weight (row-stochastic):       w = softmax_j( |prod| − λ·d² )           (which neighbours couple)
    signed unit push:                      s = −tanh(g·prod) ∈ [−1,1]               (opposite → attract)
    displacement:                          Δp_i = polarity · Σ_j w_ij·s_ij·r̂_{i→j}   (|Δp| ≤ 1, no /d²)

This is the ELECTROSTATIC complement to pack.py's STERIC heads (attract = complementary shape overlap,
repel = clash overlap): shape-fit and charge-fit are independent real filters, both bounded attention.
WATER is a round species (C≈0 → apolar). We inherit pack.py's morph+motion and add ONLY this head via a
hook, so `polarity=0, water=0` is byte-identical to the previous vivarium.

    bazel run //projects/vivarium:polar_pack -- --probe      # assembly
    bazel run //projects/vivarium:polar_pack -- --verify     # base-case identity vs PackEngine
"""

from __future__ import annotations

import argparse

import numpy as np

from config import DEFAULTS, POS_DIM, VivariumConfig
from pack import PackEngine, _ln
from rng import base_rng

WATER, ACTIVE, OIL, LIPID, AMPHI = 0, 1, 2, 3, 4
_EPS = 1e-9
# k=0 radius (physical SIZE → van der Waals contact area / polarizability), per species. Water is a
# SMALL molecule (weak dispersion) but strongly polar; oil and the amphiphile body are BULKY and
# neutral. That ordering is the hydrophobic effect: water-water is held by electrostatics, oil-oil by
# dispersion, and water gains little from wetting a nonpolar surface → it expels it.
RAD_WATER, RAD_OIL, RAD_AMPHI = 0.22, 0.60, 0.60


def _rand_unit(r, n):
    """n uniformly-distributed unit vectors on the 3-sphere (normalised Gaussians)."""
    v = r.standard_normal((n, 3))
    return v / (np.linalg.norm(v, axis=1, keepdims=True) + _EPS)


class PolarPackEngine(PackEngine):
    """pack.py's morphing blobs + a FAITHFUL electrostatic polarity head (bounded, bearing-aware) + water."""

    def __init__(self, cfg, seed, water_frac=0.4, r0=0.9, amp=0.5, polarity=0.6, pol_gain=1.2,
                 water_dipole=0.8, pol_torque=0.35, pol_morph=0.15, sink_polarity=0.0,
                 oil_frac=0.0, lipid_frac=0.0, lip_ell=0.55, k_tail=1.5, k_hydro=1.0,
                 lip_range=0.7, lip_torque=0.15, amphi_frac=0.0, amphi_charge=0.8, **kw):
        super().__init__(cfg, seed, **kw)
        self.lip_ell = lip_ell       # half-length head↔tail
        self.k_tail = k_tail         # tail–tail hydrophobic cohesion (drives the bilayer core)
        self.k_hydro = k_hydro       # hydrophobic effect: tail↔water repel + head↔water attract
        self.lip_range = lip_range   # Gaussian range λ of the lipid site forces
        self.lip_torque = lip_torque # rate a lipid reorients (head→water, tail→tails)
        self._lip_torque = None
        self.sink_polarity = sink_polarity  # electrostatics = LONGEST range → low sink (slow decay)
        self.r0 = r0                        # base radius (render only)
        self.amp = amp                      # contour amplitude (render only)
        self.polarity = polarity            # gain on the electrostatic head (0 = off → base case)
        self.pol_gain = pol_gain            # tanh sharpness of the signed attract/repel push
        self.water_dipole = water_dipole    # water's PERMANENT dipole magnitude (real water is polar)
        self.pol_torque = pol_torque        # rate water reorients its dipole toward the local field
        self.pol_morph = pol_morph          # electrostatic induced-fit: how strongly the field reshapes C
        self._pol_field = None              # per-token field direction (set by the polarity head)
        self._pol_morph = None              # per-token contour update (electrostatic energy gradient)
        # WATER is a rigid MICKEY-MOUSE molecule: a negative O body with two positive H lobes at the
        # 104.5° HOH angle — a fixed body-frame charge/shape TEMPLATE that rotates (real water is polar
        # and reorients but does not change shape). Active tokens morph freely (all harmonics).
        self._water_tpl = self._mickey_template(water_dipole)
        r = base_rng(seed + 7)
        # WATER (polar dipole) / OIL (round, apolar — nonpolar solute) / ACTIVE (morphs freely)
        u = r.random(cfg.N)
        wf, of, lf = water_frac, water_frac + oil_frac, water_frac + oil_frac + lipid_frac
        af = lf + amphi_frac
        self.species = np.where(u < wf, WATER,
                       np.where(u < of, OIL,
                       np.where(u < lf, LIPID,
                       np.where(u < af, AMPHI, ACTIVE)))).astype(int)
        # AMPHIPHILE: an ordinary token whose FIXED contour is a localized polar HEAD (charge + presence
        # concentrated on one side) fading to a featureless TAIL. No rod, no torque, no k_hydro — it is a
        # normal token; head↔water affinity is the shared polarity head, tail hydrophobicity is the shared
        # DIRECTIONAL vdW gate (the tail direction has ~0 contour → no attractive surface), and it reorients
        # in the local field exactly as water does. Membrane behaviour must EMERGE from these shared forces.
        self._amphi_q = amphi_charge
        self._amphi_tpl = self._amphi_template(amphi_charge)
        self._ai = np.where(self.species == AMPHI)[0]
        self.amphi_phi = r.uniform(0.0, 2.0 * np.pi, self._ai.size)  # head-axis orientation (like water_phi)
        self.amphi_u = _rand_unit(r, self._ai.size) if self.pd == 3 else None   # 3-D head axis
        self._oi = np.where(self.species == OIL)[0]
        self.X[self._oi, self.pd:self.pd + self.tK] = 0.0           # oil is round → C≈0 → apolar (nf≈0)
        self._li = np.where(self.species == LIPID)[0]
        self.X[self._li, self.pd:self.pd + self.tK] = 0.0           # lipid body is round (rod handled explicitly)
        ao = r.uniform(0.0, 2.0 * np.pi, self._li.size)
        self.lipid_o = np.stack([np.cos(ao), np.sin(ao)], axis=1)   # each lipid's head↔tail unit axis
        self._wi = np.where(self.species == WATER)[0]
        self.water_phi = r.uniform(0.0, 2.0 * np.pi, self._wi.size)  # each water's orientation angle
        self.water_u = _rand_unit(r, self._wi.size) if self.pd == 3 else None   # 3-D dipole axis
        if self._wi.size:
            self.X[self._wi, self.pd:self.pd + self.tK] = 0.0
            self._write_water(self.X[:, self.pd:])
        if self._ai.size:
            self.X[self._ai, self.pd:self.pd + self.tK] = 0.0
            self._write_amphi(self.X[:, self.pd:])
        self._write_radii(self.X[:, self.pd:])

    def _sh_basis(self, u):
        """Real SPHERICAL HARMONICS Y_lm(û) for l=1..K, evaluated at unit direction(s) `u` (...,3).
        Returns (..., shape_dim). This is the exact 3-D counterpart of the 2-D circular basis
        {cos kθ, sin kθ}: the grounded readout stays ⟨C, basis(bearing)⟩ — a RoPE-family relative-
        direction inner product — so Parseval (overlap = contour overlap) still holds."""
        x, y, z = u[..., 0], u[..., 1], u[..., 2]
        c1 = np.sqrt(3.0 / (4.0 * np.pi))
        out = [c1 * y, c1 * z, c1 * x]                                     # l=1  (3)
        if self.cfg.n_harmonics >= 2:
            c2 = np.sqrt(15.0 / (4.0 * np.pi))
            c3 = np.sqrt(5.0 / (16.0 * np.pi))
            c4 = np.sqrt(15.0 / (16.0 * np.pi))
            out += [c2 * x * y, c2 * y * z, c3 * (3.0 * z * z - 1.0),
                    c2 * x * z, c4 * (x * x - y * y)]                      # l=2  (5)
        return np.stack(out, axis=-1)

    def _axial_coeffs(self, u, amps):
        """Contour coefficients for an AXIALLY SYMMETRIC charge pattern around unit axis u (n,3):

            nf(v̂) = Σ_l amps[l] · P_l(u·v̂)          (P_l = Legendre polynomial)

        By the spherical-harmonic addition theorem, P_l(u·v̂) = (4π/(2l+1))·Σ_m Y_lm(u)·Y_lm(v̂), so the
        coefficients are just the SAME basis evaluated at the molecule's own axis, scaled per l. That
        makes an arbitrary axial molecule exact and cheap, with no Wigner rotation matrices:

            pure dipole  (amps = [q, 0])      → water: + toward u, − behind
            head-localised (amps = [q/2, q/2]) → amphiphile: +q at the head, ~0 at the TAIL
              (P_1 + P_2 cancel at θ=π: −q/2 + q/2 = 0), i.e. polar head, NEUTRAL tail — the
              molecule the 2-D contour could not express.
        """
        b = self._sh_basis(u)                       # (n, shape_dim) — basis at the molecule's own axis
        c = np.zeros((u.shape[0], self.tK))
        i = 0
        for l in range(1, self.cfg.n_harmonics + 1):
            n = 2 * l + 1
            if l - 1 < len(amps) and amps[l - 1] != 0.0:
                c[:, i:i + n] = amps[l - 1] * (4.0 * np.pi / n) * b[:, i:i + n]
            i += n
        return c

    @staticmethod
    def _rotate_toward(u, f, rate):
        """Turn unit axes u (n,3) toward field directions f (n,3) by `rate` — the 3-D torque. Moves
        along the TANGENTIAL component only, then renormalises, so |u| stays 1."""
        fn = np.linalg.norm(f, axis=1, keepdims=True)
        fhat = np.where(fn > 1e-9, f / np.where(fn > 1e-9, fn, 1.0), 0.0)
        tang = fhat - (np.sum(fhat * u, axis=1, keepdims=True)) * u
        v = u + rate * tang * (fn > 1e-9)
        n = np.linalg.norm(v, axis=1, keepdims=True)
        return np.where(n > 1e-9, v / np.where(n > 1e-9, n, 1.0), u)

    def _amphi_template(self, scale):
        """Body-frame contour for an AMPHIPHILE: a single localized + HEAD bump toward +x, fading to a
        featureless TAIL behind. Projected onto k≥1 harmonics (no k=0), so the tail's charge AND presence
        →0 (the constant offset is dropped) → nf(head)>0, nf(tail)≈0. The polar head H-bonds water; the
        featureless tail has no attractive surface under the directional vdW gate ⇒ hydrophobic."""
        th = np.linspace(0.0, 2.0 * np.pi, 256, endpoint=False)
        kappa = 4.0
        g = np.exp(kappa * (np.cos(th) - 1.0))            # + bump toward +x (head)
        g = g - g.mean()                                  # net neutral; k=0 dropped below → tail ≈ 0
        tpl = np.zeros(self.tK)
        for k in range(1, self.cfg.n_harmonics + 1):
            tpl[2 * (k - 1)] = 2.0 * np.mean(g * np.cos(k * th))
            tpl[2 * (k - 1) + 1] = 2.0 * np.mean(g * np.sin(k * th))
        recon = sum(tpl[2 * (k - 1)] * np.cos(k * th) + tpl[2 * (k - 1) + 1] * np.sin(k * th)
                    for k in range(1, self.cfg.n_harmonics + 1))
        return tpl * (scale / (np.max(np.abs(recon)) + 1e-9))

    def _write_amphi(self, z):
        """Write each amphiphile's rigid head template into z, rotated by its orientation amphi_phi
        (Fourier rotation: harmonic k rotates by k·φ) — identical mechanism to _write_water."""
        if not self._ai.size:
            return
        if self.pd == 3:                       # 3-D: polar HEAD along the amphiphile's axis
            z[self._ai, :self.tK] = self._axial_coeffs(
                self.amphi_u, [0.5 * self._amphi_q, 0.5 * self._amphi_q])
            return
        phi = self.amphi_phi
        for k in range(1, self.cfg.n_harmonics + 1):
            ak, bk = self._amphi_tpl[2 * (k - 1)], self._amphi_tpl[2 * (k - 1) + 1]
            ck, sk = np.cos(k * phi), np.sin(k * phi)
            z[self._ai, 2 * (k - 1)] = ak * ck - bk * sk
            z[self._ai, 2 * (k - 1) + 1] = ak * sk + bk * ck

    def _write_radii(self, z):
        """Stamp each fixed species' k=0 RADIUS (physical size → vdW contact area). Water/oil/amphiphile
        are rigid molecules, so their size is a constant of the species, rewritten every step exactly
        like their shape. Tokens with no fixed size (ACTIVE) keep whatever the morph produced."""
        r = self.cfg.shape_dim          # radius channel index within the z block
        if self._wi.size:
            z[self._wi, r] = RAD_WATER
        if self._oi.size:
            z[self._oi, r] = RAD_OIL
        if self._ai.size:
            z[self._ai, r] = RAD_AMPHI

    def _mickey_template(self, scale):
        """Body-frame contour coefficients for a water molecule: two positive H lobes at ±52.25° (the
        104.5° HOH angle) and a negative O opposite → charge nf(θ) peaks toward the H side, negative
        behind. Projected onto the K harmonics; net-neutral (no k=0). Axis (+ side) points +x."""
        th = np.linspace(0.0, 2.0 * np.pi, 256, endpoint=False)
        a = np.deg2rad(52.25)
        kappa = 7.0                                        # sharper lobes → the two H ears resolve
        g = np.exp(kappa * (np.cos(th - a) - 1.0)) + np.exp(kappa * (np.cos(th + a) - 1.0))
        g = g - g.mean()                                  # net neutral (charge sums to 0)
        tpl = np.zeros(self.tK)
        for k in range(1, self.cfg.n_harmonics + 1):
            tpl[2 * (k - 1)] = 2.0 * np.mean(g * np.cos(k * th))       # a_k
            tpl[2 * (k - 1) + 1] = 2.0 * np.mean(g * np.sin(k * th))   # b_k (≈0 by symmetry)
        recon = sum(tpl[2 * (k - 1)] * np.cos(k * th) + tpl[2 * (k - 1) + 1] * np.sin(k * th)
                    for k in range(1, self.cfg.n_harmonics + 1))
        return tpl * (scale / (np.max(np.abs(recon)) + 1e-9))          # scale peak |charge| to `scale`

    def _write_water(self, z):
        """Write each water's rigid template into shape channels z (a view of X[:,POS_DIM:]), rotated
        by its orientation angle water_phi (Fourier rotation: harmonic k rotates by k·φ)."""
        if not self._wi.size:
            return
        if self.pd == 3:                       # 3-D: a point dipole along the molecule's axis
            z[self._wi, :self.tK] = self._axial_coeffs(self.water_u, [self.water_dipole, 0.0])
            return
        phi = self.water_phi
        for k in range(1, self.cfg.n_harmonics + 1):
            ak, bk = self._water_tpl[2 * (k - 1)], self._water_tpl[2 * (k - 1) + 1]
            ck, sk = np.cos(k * phi), np.sin(k * phi)
            z[self._wi, 2 * (k - 1)] = ak * ck - bk * sk
            z[self._wi, 2 * (k - 1) + 1] = ak * sk + bk * ck

    def _lipid_force(self):
        if not self._li.size or self.pd != 2:
            return 0.0
        """Explicit amphiphile physics (Cooke–Deserno style). Each LIPID is a rod: head at −ℓ·ô, tail at
        +ℓ·ô. Conservative site forces: tail↔tail ATTRACT (hydrophobic core), tail↔water REPEL and
        head↔water ATTRACT (the hydrophobic effect). Returns the per-token centre force; stores the
        reorientation torque. Every force has its Newton-3rd reaction on water → momentum-consistent."""
        li = self._li
        N = self.cfg.N
        F = np.zeros((N, 2))
        if not li.size:
            self._lip_torque = None
            return F
        L, lam = self.L, self.lip_range
        pos = self.X[:, :self.pd]
        o = self.lipid_o
        head = pos[li] - self.lip_ell * o
        tail = pos[li] + self.lip_ell * o
        wat = pos[self._wi] if self._wi.size else np.zeros((0, 2))
        th = np.zeros(len(li))

        def force_AB(A, B):
            """unit-direction field A→B and Gaussian weight g (nA,nB); min-image."""
            d = B[None, :, :] - A[:, None, :]
            d = d - L * np.round(d / L)
            d2 = np.einsum("ijc,ijc->ij", d, d) + 1e-6
            return d / np.sqrt(d2)[..., None], np.exp(-lam * d2)

        # tail–tail cohesion (attract toward each other), symmetric, self excluded
        u, g = force_AB(tail, tail); np.fill_diagonal(g, 0.0)
        f_tail = self.k_tail * np.einsum("ij,ijc->ic", g, u)
        # tail–water repel (hydrophobic) + head–water attract (hydrophilic); reactions go onto water
        if wat.size:
            u, g = force_AB(tail, wat)
            f_tail = f_tail - self.k_hydro * np.einsum("ij,ijc->ic", g, u)     # tail away from water
            F[self._wi] += self.k_hydro * np.einsum("ij,ijc->jc", g, u)        # reaction: water pushed from tail
            u, g = force_AB(head, wat)
            f_head = self.k_hydro * np.einsum("ij,ijc->ic", g, u)             # head toward water
            F[self._wi] -= self.k_hydro * np.einsum("ij,ijc->jc", g, u)        # reaction on water (pulled)
        else:
            f_head = np.zeros_like(f_tail)
        F[li] += f_head + f_tail
        lever_h, lever_t = -self.lip_ell * o, self.lip_ell * o
        th = (lever_h[:, 0] * f_head[:, 1] - lever_h[:, 1] * f_head[:, 0]
              + lever_t[:, 0] * f_tail[:, 1] - lever_t[:, 1] * f_tail[:, 0])
        self._lip_torque = th
        return F

    def _near_face(self, C, ang):
        """⟨C, basis(ang)⟩ — the contour radius-deviation each token presents along bearing `ang` (N,N).
        >0 a prong faces that way (positive charge), <0 a valley/centre faces it (negative)."""
        K = self.cfg.n_harmonics
        nf = np.zeros_like(ang)
        for k in range(1, K + 1):
            nf = nf + C[:, 2 * (k - 1)][:, None] * np.cos(k * ang) \
                    + C[:, 2 * (k - 1) + 1][:, None] * np.sin(k * ang)
        return nf

    def _extra_force(self):
        """The electrostatic polarity head + the explicit amphiphile (lipid) forces, added to pack.py's
        step. Bounded, bearing-resolved — NO /d² kernel. Reduces to 0 when polarity=0 & no lipids."""
        lipf = self._lipid_force()          # explicit amphiphile forces (0 if no lipids)
        if self.polarity <= 0.0:
            return lipf
        cfg = self.cfg
        C = self._contour()
        delta, d2 = self._periodic_delta()                 # delta = p_i − p_j
        idx = self._neighbors(d2, cfg.n_neighbors)
        mask = np.zeros_like(d2, dtype=bool)
        np.put_along_axis(mask, idx, True, axis=1)
        np.fill_diagonal(mask, False)
        dij = -delta                                       # i → j
        dist = np.sqrt(d2 + 1e-4)
        if self.pd == 3:
            # 3-D: the bearing is a DIRECTION on the sphere, read with real spherical harmonics.
            # Identical structure to the 2-D branch — ⟨C, basis(bearing)⟩ — one dimension up.
            uij = dij / dist[..., None]
            b_ij = self._sh_basis(uij)
            nf_i = np.einsum("ic,ijc->ij", C, b_ij)
            nf_j = np.einsum("ic,ijc->ij", C, self._sh_basis(-uij)).T
        else:
            ang_ij = np.arctan2(dij[..., 1], dij[..., 0])      # bearing i→j
            ang_ji = np.arctan2(delta[..., 1], delta[..., 0])  # bearing j→i
            nf_i = self._near_face(C, ang_ij)                  # what i presents toward j
            nf_j = self._near_face(C, ang_ji).T                # what j presents toward i (transpose to (i,j))
        prod = nf_i * nf_j                                 # >0 like charges, <0 opposite
        tau = max(1e-2, self.selectivity)
        score = np.where(mask, (np.abs(prod) - cfg.dist_lambda * d2) / tau, -np.inf)
        w = self._attn(score, mask, self.sink_polarity)    # softmax weights (drive the field + morph)
        unit = dij / dist[..., None]                       # toward j
        if self.conservative:
            # CONSERVATIVE electrostatics: force_i = −Σ_j prod_ij·K(d)·û  with K=exp(−λ_p·d²). prod and K
            # are symmetric, û antisymmetric ⇒ F_ij=−F_ji ⇒ conservative. prod<0 (opposite faces) → pull
            # together, prod>0 (like) → push apart. All pairs, diagonal zeroed.
            g = np.clip(prod, -3.0, 3.0) * np.exp(-self.sink_polarity * d2)   # clip for stability
            np.fill_diagonal(g, 0.0)
            disp = -np.einsum("ij,ijc->ic", g, unit)
        else:
            s = -np.tanh(self.pol_gain * prod)             # opposite faces (prod<0) → +1 attract
            disp = np.einsum("ij,ij,ijc->ic", w, s, unit)  # Σ_j w·s·r̂  (|disp| ≤ 1)
        # electrostatic TORQUE target: a token's + face should point where neighbours present − charge
        # (nf_j(i) < 0). Stored for _post_morph to reorient dipoles (this is how real water aligns).
        self._pol_field = np.einsum("ij,ij,ijc->ic", w, -nf_j, unit)
        # electrostatic MORPH: steepest descent on the polarity energy E=Σ w·nf_i·nf_j w.r.t. the
        # contour. Since nf_i(j)=⟨C_i, basis(θ_{i→j})⟩, −∂E/∂C_i = −Σ_j w_ij·nf_j(i)·basis(θ_{i→j}) — a
        # bounded, attention-weighted sum of relative-bearing basis vectors (RoPE-family, transformer-
        # only). It grows the contour's + charge toward neighbours' − faces → electrostatically-induced
        # fit: the same field that moves a token also RESHAPES it. Stored for _post_morph.
        if self.pd == 3:
            basis = b_ij
        else:
            basis = np.zeros(d2.shape + (self.tK,))
            for k in range(1, self.cfg.n_harmonics + 1):
                basis[:, :, 2 * (k - 1)] = np.cos(k * ang_ij)
                basis[:, :, 2 * (k - 1) + 1] = np.sin(k * ang_ij)
        self._pol_morph = np.einsum("ij,ijc->ic", w * (-nf_j), basis)
        return lipf + self.polarity * disp

    def _post_morph(self, z2):
        """WATER is a permanent dipole (k=1 harmonic, fixed magnitude, higher harmonics zeroed) that
        REORIENTS toward the local field — its + face turns to point at neighbours' − charge, exactly
        as a real polar molecule aligns. No-op without water → base case unchanged."""
        # electrostatic induced-fit morph (all tokens): reshape the contour down the polarity-energy
        # gradient. Active tokens deform to charge-fit their neighbours; water is re-constrained below.
        if self.polarity > 0.0 and self._pol_morph is not None:
            z2[:, :self.tK] = z2[:, :self.tK] + self.pol_morph * self._pol_morph
        if self._oi.size:
            z2[self._oi, :self.tK] = 0.0       # OIL stays round/apolar (nonpolar solute)
        if self._li.size:
            z2[self._li, :self.tK] = 0.0       # lipid body round (the rod is handled explicitly)
            if self._lip_torque is not None:   # reorient: head→water, tail→tails
                dth = np.clip(self.lip_torque * self._lip_torque, -0.4, 0.4)
                c, s = np.cos(dth), np.sin(dth)
                ox, oy = self.lipid_o[:, 0], self.lipid_o[:, 1]
                self.lipid_o = np.stack([c * ox - s * oy, s * ox + c * oy], axis=1)
        if self._wi.size:
            # WATER keeps its rigid Mickey shape but REORIENTS: turn its +H axis toward the local field
            # (where neighbours present − charge), then rewrite the rotated template (overwrites the
            # generic morph for water — a real water molecule rotates, it doesn't deform).
            if self.polarity > 0.0 and self._pol_field is not None and self.pd == 3:
                self.water_u = self._rotate_toward(self.water_u, self._pol_field[self._wi],
                                                   self.pol_torque)
            elif self.polarity > 0.0 and self._pol_field is not None:
                fld = self._pol_field[self._wi]
                tgt = np.arctan2(fld[:, 1], fld[:, 0])                 # desired +H bearing
                d = np.arctan2(np.sin(tgt - self.water_phi), np.cos(tgt - self.water_phi))
                mag = np.linalg.norm(fld, axis=1)                      # no field → no torque
                self.water_phi = self.water_phi + self.pol_torque * d * (mag > 1e-6)
            self._write_water(z2)
        if self._ai.size:
            # AMPHIPHILE is rigid like water: turn its + HEAD toward the local field, then rewrite the
            # rotated head template (overwrites the generic morph — the head keeps its fixed shape). Same
            # dipole-aligns-in-field physics water uses; NOT a bespoke lipid torque.
            if self.polarity > 0.0 and self._pol_field is not None and self.pd == 3:
                self.amphi_u = self._rotate_toward(self.amphi_u, self._pol_field[self._ai],
                                                   self.pol_torque)
            elif self.polarity > 0.0 and self._pol_field is not None:
                fld = self._pol_field[self._ai]
                tgt = np.arctan2(fld[:, 1], fld[:, 0])
                d = np.arctan2(np.sin(tgt - self.amphi_phi), np.cos(tgt - self.amphi_phi))
                mag = np.linalg.norm(fld, axis=1)
                self.amphi_phi = self.amphi_phi + self.pol_torque * d * (mag > 1e-6)
            self._write_amphi(z2)
        self._write_radii(z2)
        return z2

    # NOTE: no step() override — we inherit PackEngine.step() and only add the two hooks above, so
    # with polarity=0 and water_frac=0 the trajectory is byte-identical to the previous vivarium.

    def amphi_head(self):
        """Unit vector along each amphiphile's HEAD direction, shape (n_amphi, POS_DIM). STABLE
        CONTRACT for the frozen benchmark harness: the harness must never need to know how the head
        orientation is stored (an angle in 2D, a vector in 3D, …), only which way each head points."""
        if not self._ai.size:
            return np.zeros((0, self.pd))
        if self.pd == 3:
            return self.amphi_u
        return np.stack([np.cos(self.amphi_phi), np.sin(self.amphi_phi)], axis=1)

    def token_polarity(self):
        """Per-token spikiness Σ_k k·(a_k²+b_k²) — the emergent polarity the viewer already colours by."""
        C = self._contour()
        K = self.cfg.n_harmonics
        pol = np.zeros(self.cfg.N)
        for k in range(1, K + 1):
            pol += k * (C[:, 2 * (k - 1)] ** 2 + C[:, 2 * (k - 1) + 1] ** 2)
        return pol

    def measure(self):
        from metrics_pack import measure as mpack
        m = mpack(self.X[:, :self.pd], self.L, radius=1.0)
        pol = self.token_polarity()
        act = self.species == ACTIVE
        return {"clusters": m["n_clusters"], "largest": round(m["largest_frac"], 3),
                "polarity": round(float(pol[act].mean()) if act.any() else 0.0, 3)}

    def snapshot(self):
        snap = super().snapshot()
        snap["species"] = [int(x) for x in self.species]        # 0 water · 1 active · 2 oil · 3 lipid
        snap["lip_ell"] = float(self.lip_ell)
        snap["lipids"] = {int(i): [float(self.lipid_o[k, 0]), float(self.lipid_o[k, 1])]
                          for k, i in enumerate(self._li)}       # per-lipid head↔tail axis (for rods)
        return snap


def render_svg(e, W=720):
    """Draw the actual contour blobs, coloured by emergent polarity (blue apolar → red polar); water
    outlined in cyan. A '+' marks each blob's brightest prong (its dominant positive charge)."""
    L, B, sc = e.L, e.cfg.pos_bound, W / (2.0 * e.cfg.pos_bound)
    X = lambda x: (x + B) * sc
    C = e._contour()
    pos = e.X[:, :e.pd]
    pol = e.token_polarity()
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}" viewBox="0 0 {W} {W}">',
             f'<rect width="{W}" height="{W}" fill="#0e131b"/>']
    th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    K = e.cfg.n_harmonics
    for i in range(e.cfg.N):
        r = e.r0 * (1.0 + e.amp * sum(C[i, 2 * (k - 1)] * np.cos(k * th)
                                      + C[i, 2 * (k - 1) + 1] * np.sin(k * th) for k in range(1, K + 1)))
        r = np.clip(r, 0.15, None)
        xs = X(pos[i, 0] + r * np.cos(th)); ys = X(pos[i, 1] + r * np.sin(th))
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        t = max(0.0, min(1.0, (pol[i] - 4.0) / 14.0))
        hue = 210 * (1 - t)
        if e.species[i] == LIPID:
            continue                                  # drawn as rods below
        if e.species[i] == WATER:
            parts.append(f'<polygon points="{pts}" fill="#1e3a5f" stroke="#38bdf8" '
                         f'stroke-width="1.3" opacity="0.85"/>')
        elif e.species[i] == OIL:
            parts.append(f'<circle cx="{X(pos[i,0]):.1f}" cy="{X(pos[i,1]):.1f}" r="{0.6*sc:.1f}" '
                         f'fill="#3f3f46" stroke="#71717a" stroke-width="1"/>')  # nonpolar oil = grey
        else:
            parts.append(f'<polygon points="{pts}" fill="hsla({hue:.0f},65%,58%,0.92)" '
                         f'stroke="#0b0e13" stroke-width="1.2"/>')
    # LIPIDS as rods: head (blue, hydrophilic) — tail (orange, hydrophobic)
    for k, i in enumerate(e._li):
        o = e.lipid_o[k]
        hx, hy = X(pos[i, 0] - e.lip_ell * o[0]), X(pos[i, 1] - e.lip_ell * o[1])
        tx, ty = X(pos[i, 0] + e.lip_ell * o[0]), X(pos[i, 1] + e.lip_ell * o[1])
        parts.append(f'<line x1="{hx:.1f}" y1="{hy:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" '
                     f'stroke="#f59e0b" stroke-width="3" opacity="0.8"/>')          # tail rod
        parts.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="3.5" fill="#f59e0b"/>')  # tail tip
        parts.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="4.5" fill="#38bdf8"/>')  # hydrophilic head
    m = e.measure()
    parts.append(f'<text x="10" y="{W-14}" fill="#cbd5e0" font-family="monospace" font-size="15">'
                 f't={e.t}  mean polarity={m["polarity"]:.2f}  clusters={m["clusters"]}  '
                 f'(blue=apolar/water · red=polar prongs)</text></svg>')
    return "\n".join(parts)


def _cfg(**over):
    return VivariumConfig(**{**DEFAULTS, **over})


_DIM_OVERRIDE = {}


def _cfgd(**over):
    """Config honouring the CLI --dim flag. In 3-D the contour uses spherical harmonics l=1..K, so
    K=2 (shape_dim 8) keeps pos3+shape8+hidden5 inside d=16, and the box shrinks to hold the same
    LIQUID density in a volume rather than an area."""
    return _cfg(**{**_DIM_OVERRIDE, **over})


def probe(a):
    e = PolarPackEngine(_cfg(), a.seed, water_frac=a.water, polarity=a.polarity, skew=a.skew,
                        sink_polarity=a.spol)
    e.sink_repel, e.sink_attract = a.srep, a.satt
    e.selectivity = a.sel
    e.temperature = a.kt
    e.conservative = a.cons
    lip = e.species == ACTIVE
    print(f" tick  polarity  clusters  largest  speed   (skew={a.skew} sel={a.sel} kt={a.kt})")
    for _ in range(0, a.ticks + 1, a.every):
        m = e.measure()
        speed = float(np.mean(np.linalg.norm(e.vel[lip], axis=1))) if lip.any() else 0.0
        print(f"{e.t:6d}   {m['polarity']:.3f}     {m['clusters']:3d}     {m['largest']:.3f}   {speed:.4f}")
        for _ in range(a.every):
            e.step()


def verify_base_case(seed=0, steps=300):
    """The base case (polarity=0, water=0) must be byte-identical to the previous vivarium (PackEngine)."""
    from pack import PackEngine
    a = PackEngine(_cfg(), seed)
    b = PolarPackEngine(_cfg(), seed, water_frac=0.0, polarity=0.0)
    for _ in range(steps):
        a.step(); b.step()
    diff = float(np.max(np.abs(a.X - b.X)))
    ok = diff == 0.0
    print(f"base-case identity vs PackEngine after {steps} steps: max|ΔX| = {diff:.2e}  "
          f"→ {'IDENTICAL ✓' if ok else 'DIFFERS ✗'}")
    return 0 if ok else 1


def water_liquid_test(a):
    """PURE water (water_frac=1): does it form ONE cohesive hydrogen-bonded LIQUID where every water
    locks to its neighbours? largest→1.0 (all connected), coord in a liquid range, hbond_frac high
    (a + H face meeting a − O face), and not frozen/collapsed."""
    from metrics_pack import measure as mpack
    e = PolarPackEngine(_cfg(), a.seed, water_frac=1.0, polarity=a.polarity, skew=0.0,
                        sink_polarity=a.spol, water_dipole=a.wcharge, repel=a.repel, attract=0.0,
                        cohesion=a.cohesion)
    e.sink_repel, e.sink_attract = a.srep, a.satt
    e.selectivity = a.sel
    e.temperature = a.kt
    e.conservative = a.cons
    e.repel_contact = a.contact
    e.momentum = a.mom
    print(f" tick  largest  nclust  coord  hbond%  speed   (pol={a.polarity} sel={a.sel} kt={a.kt} "
          f"srep={a.srep} satt={a.satt} spol={a.spol} repel={a.repel} q={a.wcharge})")
    for t in range(0, a.ticks + 1, a.every):
        pos = e.X[:, :e.pd]
        m = mpack(pos, e.L, radius=1.3)
        delta, d2 = e._periodic_delta()
        near = (d2 < 1.4 ** 2); np.fill_diagonal(near, False)
        coord = float(near.sum(1).mean())
        C = e._contour()
        dij = -delta
        nf_i = e._near_face(C, np.arctan2(dij[..., 1], dij[..., 0]))
        nf_j = e._near_face(C, np.arctan2(delta[..., 1], delta[..., 0])).T
        bonded = near & (nf_i * nf_j < 0)                  # + face meets − face = an H-bond contact
        hb = 100.0 * bonded.sum() / max(1, near.sum())
        speed = float(np.mean(np.linalg.norm(e.vel, axis=1)))
        print(f"{t:5d}   {m['largest_frac']:.3f}   {m['n_clusters']:3d}   {coord:4.1f}   {hb:4.0f}   {speed:.4f}")
        for _ in range(a.every):
            e.step()


def demix_test(a):
    """WATER + OIL: does the hydrophobic effect EMERGE? Water self-associates (electrostatics ≫ vdW) and
    should exclude the nonpolar oil → phase separation. like-frac = of each token's close neighbours,
    the fraction that are the SAME species (baseline = species fraction 0.5; →1 = fully demixed)."""
    cfg = _cfgd(N=a.n) if a.n else _cfgd()
    e = PolarPackEngine(cfg, a.seed, water_frac=0.5, oil_frac=0.5, polarity=a.polarity, skew=0.0,
                        repel=a.repel, attract=0.4, cohesion=0.0, momentum=a.mom, water_dipole=a.wcharge)
    e.sink_repel = a.srep
    e.conservative = a.cons
    e.repel_contact = a.contact
    e.sink_attract, e.sink_polarity = a.satt, a.spol
    e.selectivity, e.temperature = a.sel, a.kt
    e.attract_gated = a.gated
    sp = e.species
    print(" tick  like-frac  water-near-water  oil-near-oil   (→1 = demixed; 0.5 = mixed)")
    for t in range(0, a.ticks + 1, a.every):
        _, d2 = e._periodic_delta()
        near = (d2 < 1.6 ** 2); np.fill_diagonal(near, False)
        same = (sp[:, None] == sp[None, :])
        lf = (near & same).sum() / max(1, near.sum())
        wn = near[sp == WATER]; ww = (wn & (sp[None, :] == WATER)).sum() / max(1, wn.sum())
        on = near[sp == OIL]; oo = (on & (sp[None, :] == OIL)).sum() / max(1, on.sum())
        print(f"{t:5d}   {lf:.3f}      {ww:.3f}          {oo:.3f}")
        for _ in range(a.every):
            e.step()
    return 0


def smoke_test(a):
    """Construct the engine, step it, and print geometry — catches dimension bugs immediately."""
    cfg = _cfgd(N=a.n) if a.n else _cfgd()
    e = PolarPackEngine(cfg, a.seed, water_frac=a.water, amphi_frac=a.amphi, polarity=a.polarity,
                        repel=a.repel, attract=0.30, cohesion=0.0, skew=0.0, momentum=a.mom,
                        water_dipole=a.wcharge, amphi_charge=a.wcharge)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = a.srep, a.satt, a.spol
    e.repel_contact, e.selectivity, e.temperature = 1.0, a.sel, a.kt
    print(f"pos_dim={cfg.pos_dim} shape_dim={cfg.shape_dim} hidden={cfg.hidden_dim} "
          f"pos_bound={cfg.pos_bound} N={cfg.N}")
    print(f"X={e.X.shape} pos={e.X[:, :e.pd].shape} head={e.amphi_head().shape}")
    for _ in range(a.ticks):
        e.step()
    p = e.X[:, :e.pd]
    rng = "  ".join(f"{c}[{p[:, i].min():.1f},{p[:, i].max():.1f}]"
                    for i, c in enumerate("xyz"[:e.pd]))
    print(f"t={e.t} finite={bool(np.isfinite(e.X).all())}  {rng}")
    if e.pd == 3:
        print("water axes unit:", bool(np.allclose(np.linalg.norm(e.water_u, axis=1), 1.0, atol=1e-6)))
        print("amphi axes unit:", bool(np.allclose(np.linalg.norm(e.amphi_u, axis=1), 1.0, atol=1e-6)))
    return 0


def _amphi_order(e):
    """Self-assembly order parameters for the emergent amphiphiles. For each amphiphile, split its close
    neighbours into HEAD-side and TAIL-side (by the head vector (cosφ,sinφ)) and measure:
      head_water = fraction of HEAD-side neighbours that are water   (heads face water → high)
      tail_dry   = fraction of TAIL-side neighbours that are amphiphile (tails bury together → high)
    Baselines are the neighbour species fractions; a clean micelle/bilayer pushes both ABOVE baseline."""
    ai = e._ai
    if not ai.size:
        return None
    delta, d2 = e._periodic_delta()
    near = d2 < 1.6 ** 2
    np.fill_diagonal(near, False)
    sp = e.species
    h = e.amphi_head()          # stable contract: works in 2-D (angle) and 3-D (vector)
    hw, td = [], []
    wat_base, amp_base = [], []
    for idx, i in enumerate(ai):
        nb = np.where(near[i])[0]
        if not nb.size:
            continue
        u = -delta[i, nb]                                   # i → j
        u = u / (np.linalg.norm(u, axis=1, keepdims=True) + 1e-9)
        side = u @ h[idx]
        hs, ts = nb[side > 0], nb[side <= 0]
        wat_base.append((sp[nb] == WATER).mean()); amp_base.append((sp[nb] == AMPHI).mean())
        if hs.size:
            hw.append((sp[hs] == WATER).mean())
        if ts.size:
            td.append((sp[ts] == AMPHI).mean())
    m = lambda x: float(np.mean(x)) if x else 0.0
    return m(hw), m(td), m(wat_base), m(amp_base)


def amphi_test(a):
    """Can an amphiphile built from a NORMAL token (polar-head/neutral-tail contour, no rod/torque/k_hydro)
    self-assemble under the shared forces? Reports head_water / tail_dry vs baseline over time."""
    cfg = _cfgd(N=a.n) if a.n else _cfgd()
    e = PolarPackEngine(cfg, a.seed, water_frac=a.water, amphi_frac=a.amphi, polarity=a.polarity,
                        repel=a.repel, attract=0.30, cohesion=0.0, skew=0.0, momentum=a.mom,
                        water_dipole=a.wcharge, amphi_charge=a.wcharge)
    e.conservative = True
    e.attract_gated = a.gated                               # directional vdW → tail is hydrophobic
    e.sink_repel, e.sink_attract, e.sink_polarity = a.srep, a.satt, a.spol
    e.repel_contact, e.selectivity, e.temperature = 1.0, a.sel, a.kt
    print(f"N={e.cfg.N} water={a.water} amphi={a.amphi} polarity={a.polarity} gated={a.gated}  "
          f"(head_water/tail_dry > baseline ⇒ self-assembly)")
    print(" tick  head_water (base)   tail_dry (base)")
    for t in range(0, a.ticks + 1, a.every):
        o = _amphi_order(e)
        if o:
            hw, td, wb, ab = o
            print(f"{t:5d}    {hw:.3f}  ({wb:.3f})     {td:.3f}  ({ab:.3f})")
        for _ in range(a.every):
            e.step()
    if a.out:
        with open(a.out, "w") as f:
            f.write(render_svg(e))
        print(f"wrote {a.out}")
    return 0


def fill_test(a):
    """Does the dish stay FILLED, or condense into a drop? Mirrors the server showcase config at a
    chosen N / water_frac and reports late-time occupancy + radius-of-gyration. Rg→4.90 (= the value
    for a uniform fill of [−6,6]²) means space-filling; Rg well below that means a condensed clump."""
    cfg = _cfgd(N=a.n) if a.n else _cfgd()
    lip = a.lipid if a.lipid else 0.0
    e = PolarPackEngine(cfg, a.seed, water_frac=a.water, lipid_frac=lip, repel=a.repel, attract=0.30,
                        polarity=0.80, cohesion=0.0, skew=0.0, morph=0.70, momentum=0.30, speed=1.20)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, 1.0, 0.25
    e.repel_contact, e.rigidity, e.selectivity, e.temperature = 1.0, 0.0, 0.30, 0.05
    e.k_tail, e.k_hydro = 1.5, 1.0
    B = e.cfg.pos_bound
    n_uniform = round((2 * B) ** 2 / (np.pi * 0.5 ** 2))  # disks of Ø=1 that tile the box (~packing 1)
    print(f"N={e.cfg.N}  water={a.water}  lipid={lip}  repel={a.repel}   "
          f"(a full box ≈ {n_uniform} tokens; Rg_uniform=4.90)")
    print(" tick  occ(/64)  Rg    largest   (occ high + Rg~4.9 = fills; low = clumped)")
    for t in range(0, a.ticks + 1, a.every):
        p = e.X[:, :2]
        cx, cy = p[:, 0].mean(), p[:, 1].mean()
        rg = float(np.sqrt(((p[:, 0] - cx) ** 2 + (p[:, 1] - cy) ** 2).mean()))
        gx = np.floor((p[:, 0] + B) / (2 * B) * 8).clip(0, 7).astype(int)
        gy = np.floor((p[:, 1] + B) / (2 * B) * 8).clip(0, 7).astype(int)
        occ = len(set(zip(gx.tolist(), gy.tolist())))
        m = e.measure()
        print(f"{t:5d}    {occ:2d}/64   {rg:.2f}   {m['largest']:.3f}")
        for _ in range(a.every):
            e.step()
    if a.out:
        with open(a.out, "w") as f:
            f.write(render_svg(e))
        print(f"wrote {a.out}")
    return 0


def decay_check():
    """Show that the attract force now DECAYS with distance once the sink is on (and did NOT before).
    Single neighbour at separation d, fixed complementary-fit content; force proxy = weight × d."""
    e = PolarPackEngine(_cfg(), 0)
    lam, tau = e.cfg.dist_lambda, 0.3
    mask = np.array([[False, True], [True, False]])
    print(" sep   attract force:  sink=0 (old)   sink=2   sink=4")
    for d in (1.0, 2.0, 3.0, 4.0, 6.0, 8.0):
        d2 = np.array([[0.0, d * d], [d * d, 0.0]])
        score = np.where(mask, (1.0 - lam * d2) / tau, -np.inf)
        vals = []
        for sk in (0.0, 2.0, 4.0):
            A = e._attn(score, mask, sk)
            vals.append(A[0, 1] * d)                       # weight × separation = attract magnitude
        print(f" {d:4.1f}      {vals[0]:12.4f}   {vals[1]:6.4f}   {vals[2]:6.4f}")
    print("sink=0 GROWS with distance (spring, the bug); sink>0 rises then DECAYS to ~0 (physical).")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    p.add_argument("--decay", action="store_true")
    p.add_argument("--watertest", action="store_true")
    p.add_argument("--fill", action="store_true", help="does the dish stay filled or condense?")
    p.add_argument("--n", type=int, default=0, help="override token count N (0 = config default)")
    p.add_argument("--gated", action="store_true", help="vdW attraction scales with contour presence")
    p.add_argument("--amphitest", action="store_true", help="emergent amphiphile self-assembly test")
    p.add_argument("--amphi", type=float, default=0.15, help="amphiphile fraction")
    p.add_argument("--dim", type=int, default=2, choices=(2, 3), help="dish dimensionality")
    p.add_argument("--smoke", action="store_true", help="smoke-test the engine and print geometry")
    p.add_argument("--demix", action="store_true")
    p.add_argument("--wcharge", type=float, default=0.8)
    p.add_argument("--repel", type=float, default=0.2)
    p.add_argument("--oil", type=float, default=0.0)
    p.add_argument("--lipid", type=float, default=0.0)
    p.add_argument("--cons", action="store_true", help="conservative symmetric forces")
    p.add_argument("--contact", type=float, default=0.0, help="repel_contact (overlap distance)")
    p.add_argument("--mom", type=float, default=0.3, help="momentum (overdamped ~0.3)")
    p.add_argument("--cohesion", type=float, default=0.08)
    p.add_argument("--probe", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ticks", type=int, default=2000)
    p.add_argument("--every", type=int, default=400)
    p.add_argument("--water", type=float, default=0.4)
    p.add_argument("--polarity", type=float, default=0.6)
    p.add_argument("--skew", type=float, default=0.0)
    p.add_argument("--sel", type=float, default=0.3, help="softmax selectivity τ (NOT temperature)")
    p.add_argument("--kt", type=float, default=0.0, help="real temperature = thermal Langevin noise")
    p.add_argument("--srep", type=float, default=4.0, help="repel sink (short range, fast decay)")
    p.add_argument("--satt", type=float, default=3.0, help="attract sink (short range)")
    p.add_argument("--spol", type=float, default=0.5, help="polarity sink (long range, slow decay)")
    p.add_argument("--out", default=None, help="render final frame to this SVG path")
    a = p.parse_args(argv)
    if a.dim == 3:
        # 3-D: K=2 spherical harmonics, and pos_bound shrunk so N tokens fill a VOLUME at the same
        # number density the 2-D benchmark had in its area (else the dish is a dilute gas).
        _DIM_OVERRIDE.update(pos_dim=3, n_harmonics=2, pos_bound=3.0)
    if a.smoke:
        return smoke_test(a)
    if a.decay:
        return decay_check()
    if a.watertest:
        return water_liquid_test(a)
    if a.fill:
        return fill_test(a)
    if a.amphitest:
        return amphi_test(a)
    if a.demix:
        return demix_test(a)
    if a.verify:
        return verify_base_case()
    if a.out:
        attract = 0.0 if a.water >= 0.999 else 0.4
        e = PolarPackEngine(_cfg(), a.seed, water_frac=a.water, oil_frac=a.oil, lipid_frac=a.lipid, polarity=a.polarity,
                            skew=a.skew, sink_polarity=a.spol, repel=a.repel, cohesion=a.cohesion,
                            attract=attract, water_dipole=a.wcharge)
        e.sink_repel, e.sink_attract = a.srep, a.satt
        e.selectivity = a.sel
        e.temperature = a.kt
        e.conservative = a.cons
        e.repel_contact = a.contact
        e.momentum = a.mom
        for _ in range(a.ticks):
            e.step()
        with open(a.out, "w") as f:
            f.write(render_svg(e))
        m = e.measure()
        print(f"wrote {a.out}  polarity={m['polarity']:.2f} clusters={m['clusters']}")
    else:
        probe(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
