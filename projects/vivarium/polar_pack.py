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

WATER, ACTIVE = 0, 1
_EPS = 1e-9


class PolarPackEngine(PackEngine):
    """pack.py's morphing blobs + a FAITHFUL electrostatic polarity head (bounded, bearing-aware) + water."""

    def __init__(self, cfg, seed, water_frac=0.4, r0=0.9, amp=0.5, polarity=0.6, pol_gain=1.2,
                 water_dipole=0.8, pol_torque=0.35, pol_morph=0.15, sink_polarity=0.0, **kw):
        super().__init__(cfg, seed, **kw)
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
        self.species = (r.random(cfg.N) > water_frac).astype(int)   # 1 active (morphs), 0 water
        self._wi = np.where(self.species == WATER)[0]
        self.water_phi = r.uniform(0.0, 2.0 * np.pi, self._wi.size)  # each water's orientation angle
        if self._wi.size:
            self.X[self._wi, POS_DIM:POS_DIM + self.tK] = 0.0
            self._write_water(self.X[:, POS_DIM:])

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
        phi = self.water_phi
        for k in range(1, self.cfg.n_harmonics + 1):
            ak, bk = self._water_tpl[2 * (k - 1)], self._water_tpl[2 * (k - 1) + 1]
            ck, sk = np.cos(k * phi), np.sin(k * phi)
            z[self._wi, 2 * (k - 1)] = ak * ck - bk * sk
            z[self._wi, 2 * (k - 1) + 1] = ak * sk + bk * ck

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
        """The electrostatic polarity head, added to pack.py's step. Bounded softmax attention over the
        bearing-resolved near-face charges — NO /d² kernel. Returns 0 when polarity=0 (base case)."""
        if self.polarity <= 0.0:
            return 0.0
        cfg = self.cfg
        C = self._contour()
        delta, d2 = self._periodic_delta()                 # delta = p_i − p_j
        idx = self._neighbors(d2, cfg.n_neighbors)
        mask = np.zeros_like(d2, dtype=bool)
        np.put_along_axis(mask, idx, True, axis=1)
        np.fill_diagonal(mask, False)
        dij = -delta                                       # i → j
        dist = np.sqrt(d2 + 1e-4)
        ang_ij = np.arctan2(dij[..., 1], dij[..., 0])      # bearing i→j
        ang_ji = np.arctan2(delta[..., 1], delta[..., 0])  # bearing j→i
        nf_i = self._near_face(C, ang_ij)                  # what i presents toward j
        nf_j = self._near_face(C, ang_ji).T                # what j presents toward i (transpose to (i,j))
        prod = nf_i * nf_j                                 # >0 like charges, <0 opposite
        tau = max(1e-2, self.selectivity)
        score = np.where(mask, (np.abs(prod) - cfg.dist_lambda * d2) / tau, -np.inf)
        w = self._attn(score, mask, self.sink_polarity)    # sink-aware bounded → decays with distance
        s = -np.tanh(self.pol_gain * prod)                 # opposite faces (prod<0) → +1 attract
        unit = dij / dist[..., None]
        disp = np.einsum("ij,ij,ijc->ic", w, s, unit)      # Σ_j w·s·r̂  (|disp| ≤ 1)
        # electrostatic TORQUE target: a token's + face should point where neighbours present − charge
        # (nf_j(i) < 0). Stored for _post_morph to reorient dipoles (this is how real water aligns).
        self._pol_field = np.einsum("ij,ij,ijc->ic", w, -nf_j, unit)
        # electrostatic MORPH: steepest descent on the polarity energy E=Σ w·nf_i·nf_j w.r.t. the
        # contour. Since nf_i(j)=⟨C_i, basis(θ_{i→j})⟩, −∂E/∂C_i = −Σ_j w_ij·nf_j(i)·basis(θ_{i→j}) — a
        # bounded, attention-weighted sum of relative-bearing basis vectors (RoPE-family, transformer-
        # only). It grows the contour's + charge toward neighbours' − faces → electrostatically-induced
        # fit: the same field that moves a token also RESHAPES it. Stored for _post_morph.
        basis = np.zeros(d2.shape + (self.tK,))
        for k in range(1, self.cfg.n_harmonics + 1):
            basis[:, :, 2 * (k - 1)] = np.cos(k * ang_ij)
            basis[:, :, 2 * (k - 1) + 1] = np.sin(k * ang_ij)
        self._pol_morph = np.einsum("ij,ijc->ic", w * (-nf_j), basis)
        return self.polarity * disp

    def _post_morph(self, z2):
        """WATER is a permanent dipole (k=1 harmonic, fixed magnitude, higher harmonics zeroed) that
        REORIENTS toward the local field — its + face turns to point at neighbours' − charge, exactly
        as a real polar molecule aligns. No-op without water → base case unchanged."""
        # electrostatic induced-fit morph (all tokens): reshape the contour down the polarity-energy
        # gradient. Active tokens deform to charge-fit their neighbours; water is re-constrained below.
        if self.polarity > 0.0 and self._pol_morph is not None:
            z2[:, :self.tK] = z2[:, :self.tK] + self.pol_morph * self._pol_morph
        if self._wi.size:
            # WATER keeps its rigid Mickey shape but REORIENTS: turn its +H axis toward the local field
            # (where neighbours present − charge), then rewrite the rotated template (overwrites the
            # generic morph for water — a real water molecule rotates, it doesn't deform).
            if self.polarity > 0.0 and self._pol_field is not None:
                fld = self._pol_field[self._wi]
                tgt = np.arctan2(fld[:, 1], fld[:, 0])                 # desired +H bearing
                d = np.arctan2(np.sin(tgt - self.water_phi), np.cos(tgt - self.water_phi))
                mag = np.linalg.norm(fld, axis=1)                      # no field → no torque
                self.water_phi = self.water_phi + self.pol_torque * d * (mag > 1e-6)
            self._write_water(z2)
        return z2

    # NOTE: no step() override — we inherit PackEngine.step() and only add the two hooks above, so
    # with polarity=0 and water_frac=0 the trajectory is byte-identical to the previous vivarium.

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
        m = mpack(self.X[:, :POS_DIM], self.L, radius=1.0)
        pol = self.token_polarity()
        act = self.species == ACTIVE
        return {"clusters": m["n_clusters"], "largest": round(m["largest_frac"], 3),
                "polarity": round(float(pol[act].mean()) if act.any() else 0.0, 3)}


def render_svg(e, W=720):
    """Draw the actual contour blobs, coloured by emergent polarity (blue apolar → red polar); water
    outlined in cyan. A '+' marks each blob's brightest prong (its dominant positive charge)."""
    L, B, sc = e.L, e.cfg.pos_bound, W / (2.0 * e.cfg.pos_bound)
    X = lambda x: (x + B) * sc
    C = e._contour()
    pos = e.X[:, :POS_DIM]
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
        if e.species[i] == WATER:
            parts.append(f'<polygon points="{pts}" fill="#1e3a5f" stroke="#38bdf8" '
                         f'stroke-width="1.3" opacity="0.85"/>')
        else:
            parts.append(f'<polygon points="{pts}" fill="hsla({hue:.0f},65%,58%,0.92)" '
                         f'stroke="#0b0e13" stroke-width="1.2"/>')
    m = e.measure()
    parts.append(f'<text x="10" y="{W-14}" fill="#cbd5e0" font-family="monospace" font-size="15">'
                 f't={e.t}  mean polarity={m["polarity"]:.2f}  clusters={m["clusters"]}  '
                 f'(blue=apolar/water · red=polar prongs)</text></svg>')
    return "\n".join(parts)


def _cfg(**over):
    return VivariumConfig(**{**DEFAULTS, **over})


def probe(a):
    e = PolarPackEngine(_cfg(), a.seed, water_frac=a.water, polarity=a.polarity, skew=a.skew,
                        sink_polarity=a.spol)
    e.sink_repel, e.sink_attract = a.srep, a.satt
    e.selectivity = a.sel
    e.temperature = a.kt
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
    print(f" tick  largest  nclust  coord  hbond%  speed   (pol={a.polarity} sel={a.sel} kt={a.kt} "
          f"srep={a.srep} satt={a.satt} spol={a.spol} repel={a.repel} q={a.wcharge})")
    for t in range(0, a.ticks + 1, a.every):
        pos = e.X[:, :POS_DIM]
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
    p.add_argument("--wcharge", type=float, default=0.8)
    p.add_argument("--repel", type=float, default=0.2)
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
    if a.decay:
        return decay_check()
    if a.watertest:
        return water_liquid_test(a)
    if a.verify:
        return verify_base_case()
    if a.out:
        attract = 0.0 if a.water >= 0.999 else 0.4
        e = PolarPackEngine(_cfg(), a.seed, water_frac=a.water, polarity=a.polarity, skew=a.skew,
                            sink_polarity=a.spol, repel=a.repel, cohesion=a.cohesion, attract=attract,
                            water_dipole=a.wcharge)
        e.sink_repel, e.sink_attract = a.srep, a.satt
        e.selectivity = a.sel
        e.temperature = a.kt
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
