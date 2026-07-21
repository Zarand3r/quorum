"""Charged amphiphiles + water — polarity from the token's SHAPE (charge on the contour), β=0.

The idea (user's): make the token a charged shape — a NEGATIVE centre with POSITIVE extending lobes —
and add water. Then the hydrophobic effect need not be hand-coded: it EMERGES from electrostatics +
excluded volume, and the polarity is a property of the drawn shape, not a bolted-on vector.

  WATER  = a radially polar token: centre charge −K·q, K positive lobes +q around it (net neutral).
           This is exactly "centre negative, extending lobes positive".
  LIPID  = "a water molecule that grew a tail": the SAME charged head group offset to +ℓ·ô, plus a
           NEUTRAL tail bead at −ℓ·ô. Its orientation ô (head axis) is read from where the charge sits.

Law (all pairwise over charge points, min-image on a torus):
  • Coulomb  mag = −k_e·q_a·q_b/(d²+soft)   → opposite charges attract (water⇄water, water⇄head cluster)
  • excluded volume  mag = −k_rep·(σ−d)⁺    → every point has size; the neutral tail can't be dissolved
Both are SYMMETRIC functions of (relative position, charge, type) — i.e. relative-position attention
scores (value = r̂, weight = a charge/type-bilinear, distance-kernelled logit), not force kernels — so
the total force is the gradient of an energy ⇒ overdamped dynamics MINIMISE it ⇒ the structure SETTLES
(this is the β=0, conservative end of the non-reciprocity dial). Same-token point pairs are excluded
(a rigid shape's own charges must not act on each other). Polar heads + water form a charged fluid; the
neutral tails are EXCLUDED from it → tails segregate → the hydrophobic effect is emergent.

    bazel run //projects/vivarium:charged -- --probe
"""

from __future__ import annotations

import argparse

import numpy as np

from rng import base_rng

WATER, LIPID = 0, 1
_EPS = 1e-12


def _unit(v, axis=-1):
    return v / (np.linalg.norm(v, axis=axis, keepdims=True) + 1e-9)


class ChargedEngine:
    """N charged-shape tokens (water + amphiphile lipids), overdamped on a torus. Conservative."""

    def __init__(self, seed, N=80, pos_bound=6.0, water_frac=0.5,
                 K=3, q=1.0, lobe_r=0.34, ell=0.5, sigma=0.52,
                 k_e=0.30, k_rep=2.2, soft=0.15,
                 mu=0.012, mu_rot=0.06, temp=0.10, anneal=9000, maxstep=0.14, r_neigh=1.6):
        self.N = N
        self.pos_bound = pos_bound
        self.L = 2.0 * pos_bound
        self.K = K              # positive lobes per charged head
        self.q = q              # lobe charge (+q); the balancing centre is −K·q
        self.lobe_r = lobe_r    # lobe radius from the head centre
        self.ell = ell          # head/tail offset from the token centre along ô
        self.sigma = sigma      # excluded-volume diameter (per point)
        self.k_e = k_e          # Coulomb strength
        self.k_rep = k_rep      # excluded-volume stiffness
        self.soft = soft        # Coulomb softening (avoids 1/0)
        self.mu = mu
        self.mu_rot = mu_rot
        self.temp = temp
        self.anneal = anneal
        self.maxstep = maxstep
        self.r_neigh = r_neigh
        r = base_rng(seed)
        self.rng = base_rng(seed + 991)
        self.species = (r.random(N) > water_frac).astype(int)   # 1 = lipid, 0 = water
        self.pos = r.uniform(-pos_bound, pos_bound, (N, 2))
        o = r.standard_normal((N, 2))
        self.orient = _unit(o)                                  # head axis (used by lipids)
        self.vel = np.zeros((N, 2))                             # last displacement (viewer readout)
        self.t = 0
        # body-frame charge templates (before rotation): list of (offset_x, offset_y, charge)
        ang = [2.0 * np.pi * k / K for k in range(K)]
        self._water_tpl = [(0.0, 0.0, -K * q)] + [(lobe_r * np.cos(a), lobe_r * np.sin(a), q) for a in ang]
        # lipid: charged head group offset to +ℓ (head along +ô), neutral tail bead at −ℓ
        self._lipid_tpl = ([(ell, 0.0, -K * q)]
                           + [(ell + lobe_r * np.cos(a), lobe_r * np.sin(a), q) for a in ang]
                           + [(-ell, 0.0, 0.0)])   # neutral tail (excluded volume only)

    def _points(self):
        """Build (point_pos, charge, owner, lever) by rotating each token's template into the lab frame."""
        is_lip = self.species == LIPID
        cos = self.orient[:, 0]
        sin = self.orient[:, 1]
        pp, ch, own, lev = [], [], [], []
        for tpl, sel in ((self._water_tpl, ~is_lip), (self._lipid_tpl, is_lip)):
            idx = np.where(sel)[0]
            if idx.size == 0:
                continue
            c, s = cos[idx], sin[idx]
            for ox, oy, qc in tpl:
                # rotate body-frame offset (ox,oy) by the token orientation, then translate
                lx = ox * c - oy * s
                ly = ox * s + oy * c
                pp.append(self.pos[idx] + np.stack([lx, ly], axis=1))
                ch.append(np.full(idx.size, qc))
                own.append(idx)
                lev.append(np.stack([lx, ly], axis=1))
        return (np.concatenate(pp, 0), np.concatenate(ch), np.concatenate(own), np.concatenate(lev, 0))

    def step(self):
        pp, ch, own, lev = self._points()
        d = pp[None, :, :] - pp[:, None, :]                 # j − i
        d = d - self.L * np.round(d / self.L)               # min image
        dist2 = np.einsum("ijc,ijc->ij", d, d) + _EPS
        dist = np.sqrt(dist2)
        rhat = d / dist[..., None]
        np.fill_diagonal(dist, np.inf)

        qq = ch[:, None] * ch[None, :]
        coulomb = -self.k_e * qq / (dist2 + self.soft)      # + along r̂ when opposite signs → attract
        overlap = np.clip(self.sigma - dist, 0.0, None)
        rep = -self.k_rep * overlap                         # − along r̂ → push apart
        same = own[:, None] == own[None, :]                 # a rigid shape's own points don't interact
        mag = np.where(same, 0.0, coulomb + rep)
        fb = np.einsum("ij,ijc->ic", mag, rhat)             # force per point

        N = self.N
        F = np.zeros((N, 2))
        np.add.at(F, own, fb)
        torque = lev[:, 0] * fb[:, 1] - lev[:, 1] * fb[:, 0]
        T = np.zeros(N)
        np.add.at(T, own, torque)

        disp = self.mu * F
        cur = self.temp * max(0.0, 1.0 - self.t / self.anneal)
        if cur > 0.0:
            disp = disp + cur * self.mu * self.rng.standard_normal((N, 2))
        sp = np.linalg.norm(disp, axis=1, keepdims=True)
        disp = np.where(sp > self.maxstep, disp * self.maxstep / (sp + 1e-12), disp)
        self.vel = disp
        p = self.pos + disp
        self.pos = ((p + self.pos_bound) % self.L) - self.pos_bound

        dtheta = np.clip(self.mu_rot * T, -0.4, 0.4)
        c, s = np.cos(dtheta), np.sin(dtheta)
        ox, oy = self.orient[:, 0], self.orient[:, 1]
        self.orient = _unit(np.stack([c * ox - s * oy, s * ox + c * oy], axis=1))
        self.t += 1

    def view_points(self):
        """For the live viewer: charge points as [x, y, sign] (sign ∈ {−1,0,+1}), plus lipid whiskers
        as [hx, hy, tx, ty] (head→tail). Cheap, small JSON."""
        pp, ch, _, _ = self._points()
        sign = np.sign(ch).astype(int)
        pts = [[round(float(pp[k, 0]), 3), round(float(pp[k, 1]), 3), int(sign[k])]
               for k in range(pp.shape[0])]
        whisk = []
        for i in np.where(self.species == LIPID)[0]:
            p, o = self.pos[i], self.orient[i]
            whisk.append([round(float(p[0] + self.ell * o[0]), 3), round(float(p[1] + self.ell * o[1]), 3),
                          round(float(p[0] - self.ell * o[0]), 3), round(float(p[1] - self.ell * o[1]), 3)])
        return pts, whisk

    def measure(self):
        from metrics_membrane import measure
        m = measure(self.pos, self.species, self.orient, self.L, self.r_neigh)
        m["demix"] = round(self._demix(), 3)
        return m

    def _demix(self) -> float:
        """Fraction of each lipid's TAIL-side neighbours that are lipid (not water) — tails hiding from
        water. →1 means tails buried in lipid, water pushed to the head side (the hydrophobic effect)."""
        from metrics_membrane import LIPID as _L
        sp = self.species
        lip = np.where(sp == _L)[0]
        if lip.size == 0:
            return 0.0
        d = self.pos[None, :, :] - self.pos[:, None, :]
        d = d - self.L * np.round(d / self.L)
        d2 = np.einsum("ijc,ijc->ij", d, d)
        near = (d2 < 1.7 ** 2)
        np.fill_diagonal(near, False)
        dist = np.sqrt(d2 + 1e-9)
        rh = d / dist[..., None]
        vals = []
        for i in lip:
            nb = near[i]
            if not nb.any():
                continue
            tail_w = np.maximum(0.0, -(rh[i] @ self.orient[i])) * nb   # −ô side = tail
            denom = tail_w.sum()
            if denom < 1e-9:
                continue
            vals.append(float((tail_w * (sp == _L)).sum() / denom))
        return float(np.mean(vals)) if vals else 0.0


def render_svg(e, W=720):
    """Draw the charge points: + red, − blue, neutral tail grey; a faint line marks each lipid's ô."""
    L, B, s = e.L, e.pos_bound, W / e.L
    X = lambda x: (x + B) * s
    pp, ch, own, _ = e._points()
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}" viewBox="0 0 {W} {W}">',
             f'<rect width="{W}" height="{W}" fill="#0b1220"/>']
    # lipid orientation whiskers (head → tail)
    is_lip = e.species == LIPID
    for i in np.where(is_lip)[0]:
        p, o = e.pos[i], e.orient[i]
        hx, hy = X(p[0] + e.ell * o[0]), X(p[1] + e.ell * o[1])
        tx, ty = X(p[0] - e.ell * o[0]), X(p[1] - e.ell * o[1])
        if abs(hx - tx) < W / 2 and abs(hy - ty) < W / 2:
            parts.append(f'<line x1="{hx:.1f}" y1="{hy:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" '
                         f'stroke="#334155" stroke-width="1.5"/>')
    for k in range(pp.shape[0]):
        x, y, c = X(pp[k, 0]), X(pp[k, 1]), ch[k]
        col = "#e53e3e" if c > 1e-6 else ("#3b82f6" if c < -1e-6 else "#64748b")
        rad = 3.6 if c < -1e-6 else (2.6 if c > 1e-6 else 3.0)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad}" fill="{col}" opacity="0.9"/>')
    m = e.measure()
    parts.append(f'<text x="10" y="{W-14}" fill="#cbd5e0" font-family="monospace" font-size="15">'
                 f't={e.t}  demix={m["demix"]:.3f}  clusters={m["n_lipid_clusters"]}  '
                 f'(+ red  − blue  tail grey)</text></svg>')
    return "\n".join(parts)


def _cfg(a):
    return dict(N=a.N, water_frac=a.water, K=a.K, k_e=a.ke, k_rep=a.krep, sigma=a.sigma,
               ell=a.ell, mu=a.mu, temp=a.temp, anneal=a.anneal)


def probe(a):
    e = ChargedEngine(a.seed, **_cfg(a))
    lip = (e.species == LIPID)
    print(" tick  demix  side  clust  speed  drift   (demix→1 tails buried; speed→0 settled)")
    for _ in range(0, a.ticks + 1, a.every):
        m = e.measure()
        v = e.vel[lip]
        speed = float(np.mean(np.linalg.norm(v, axis=1))) if lip.any() else 0.0
        drift = float(np.linalg.norm(e.vel.mean(0)))
        print(f"{e.t:6d}  {m['demix']:.3f}  {m['side']:.3f}  {m['n_lipid_clusters']:3d}   "
              f"{speed:.4f}  {drift:.4f}")
        for _ in range(a.every):
            e.step()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--probe", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ticks", type=int, default=12000)
    p.add_argument("--every", type=int, default=1500)
    p.add_argument("--N", type=int, default=80)
    p.add_argument("--water", type=float, default=0.5)
    p.add_argument("--K", type=int, default=3)
    p.add_argument("--ke", type=float, default=0.22)
    p.add_argument("--krep", type=float, default=2.2)
    p.add_argument("--sigma", type=float, default=0.52)
    p.add_argument("--ell", type=float, default=0.5)
    p.add_argument("--mu", type=float, default=0.012)
    p.add_argument("--temp", type=float, default=0.10)
    p.add_argument("--anneal", type=int, default=9000)
    p.add_argument("--out", default=None, help="render final frame to this SVG path")
    a = p.parse_args(argv)
    if a.out:
        e = ChargedEngine(a.seed, **_cfg(a))
        for _ in range(a.ticks):
            e.step()
        with open(a.out, "w") as f:
            f.write(render_svg(e))
        m = e.measure()
        print(f"wrote {a.out}  demix={m['demix']:.3f} clusters={m['n_lipid_clusters']}")
    else:
        probe(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
