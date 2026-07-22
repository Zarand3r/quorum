"""Polarity that EMERGES from the morphing contour blob — the user's actual idea.

The grounded-contour tokens of `pack.py` start spherical and MORPH into pronged shapes (K=3 → up to
three protrusions). Here the charge is a FUNCTIONAL of that live contour, not a bolted-on template:

    r_i(θ) = R0 · (1 + Σ_k a_k cos kθ + b_k sin kθ)        the drawn blob (a_k,b_k = shape channels)
    positive charge at each boundary point ∝ r_i(θ)         → concentrated at the PROTRUSIONS (+)
    a single negative charge −Q at the centre x_i           → the body is negative (−)

So a round blob is radially polar (uniform + rim, − centre); as it morphs a prong, positive charge
gathers at the prong tip → the blob becomes POLAR *because it deformed*. Polarity = the same spikiness
the viewer already colours by. Add WATER (a species kept round → radially polar), and the charges drive
assembly: a prong (+) of one blob is pulled onto the negative centre of a neighbour (opposite attract),
prongs repel prongs. Interaction = Coulomb over the contour-derived charge points = a symmetric
relative-position attention readout (β=0, conservative); excluded volume is pack.py's bounded repel.

We inherit pack.py's real morph+motion and ADD the charge force; water's shape is frozen round.

    bazel run //projects/vivarium:polar_pack -- --probe
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
    """pack.py's morphing blobs + a charge read off the contour (protrusions +, centre −) + water."""

    def __init__(self, cfg, seed, water_frac=0.4, m_samples=10, r0=0.9, amp=0.5,
                 charge=0.6, soft=0.2, charge_k=None, **kw):
        super().__init__(cfg, seed, **kw)
        self.m_samples = m_samples          # boundary sample points per blob
        self.r0 = r0                        # base radius (world units)
        self.amp = amp                      # contour amplitude (how far prongs stick out)
        self.charge = charge                # Coulomb gain on the contour charges
        self.soft = soft                    # Coulomb softening
        self.charge_k = charge_k or min(12, cfg.N - 1)   # neighbours for the charge sum
        r = base_rng(seed + 7)
        self.species = (r.random(cfg.N) > water_frac).astype(int)   # 1 active (morphs), 0 water (round)
        self.X[self.species == WATER, POS_DIM:POS_DIM + self.tK] = 0.0   # water starts (stays) round
        th = np.linspace(0.0, 2.0 * np.pi, m_samples, endpoint=False)
        self._th = th
        K = cfg.n_harmonics
        # angular basis for r(θ): columns ordered (cos1,sin1,cos2,sin2,…) to match the shape channels
        basis = np.zeros((m_samples, 2 * K))
        for k in range(1, K + 1):
            basis[:, 2 * (k - 1)] = np.cos(k * th)
            basis[:, 2 * (k - 1) + 1] = np.sin(k * th)
        self._basis = basis
        self._dir = np.stack([np.cos(th), np.sin(th)], axis=1)      # (M,2) outward unit directions

    def _charge_points(self):
        """From each blob's live contour: M boundary + charges (∝ radius, concentrated at prongs) and
        one centre − charge. Returns (point_pos, charge, owner)."""
        C = self._contour()                                  # (N, 2K)
        pos = self.X[:, :POS_DIM]
        rad = self.r0 * (1.0 + self.amp * (C @ self._basis.T))   # (N, M) radius at each angle
        rad = np.clip(rad, 0.15, None)
        wsum = rad.sum(1, keepdims=True) + _EPS
        qpos = rad / wsum                                    # positive charge per boundary point (Σ=1)
        # boundary point positions: centre + r·direction (broadcast (N,M,2))
        bpts = pos[:, None, :] + rad[:, :, None] * self._dir[None, :, :]
        N, M = rad.shape
        pp = np.concatenate([bpts.reshape(N * M, 2), pos], axis=0)
        ch = np.concatenate([qpos.reshape(N * M), -np.ones(N)], axis=0)   # + rim, − centre (net 0)
        own = np.concatenate([np.repeat(np.arange(N), M), np.arange(N)])
        return pp, ch, own

    def _charge_force(self):
        """Coulomb between charge points of DIFFERENT blobs → net force per token. Conservative."""
        pp, ch, own = self._charge_points()
        d = pp[None, :, :] - pp[:, None, :]
        d = d - self.L * np.round(d / self.L)
        d2 = np.einsum("ijc,ijc->ij", d, d) + _EPS
        rhat = d / np.sqrt(d2)[..., None]
        qq = ch[:, None] * ch[None, :]
        mag = -self.charge * qq / (d2 + self.soft)           # + along r̂ when opposite → attract
        same = own[:, None] == own[None, :]
        mag = np.where(same, 0.0, mag)
        fb = np.einsum("ij,ijc->ic", mag, rhat)              # per charge point
        F = np.zeros((self.cfg.N, POS_DIM))
        np.add.at(F, own, fb)
        return F

    def step(self):
        cfg = self.cfg
        tau = max(1e-2, self.temperature)
        C = self._contour()
        delta, d2 = self._periodic_delta()
        idx = self._neighbors(d2, cfg.n_neighbors)
        mask = np.zeros_like(d2, dtype=bool)
        np.put_along_axis(mask, idx, True, axis=1)
        np.fill_diagonal(mask, False)
        S_direct = (C @ C.T) / np.sqrt(self.tK)
        S_comp = (C @ (C @ self.M).T) / np.sqrt(self.tK)

        # bounded repulsive attention = soft excluded volume (unchanged from pack.py)
        rscore = np.where(mask, (S_direct - cfg.dist_lambda * d2) / tau, -np.inf)
        rm = np.max(rscore, axis=1, keepdims=True)
        rm = np.where(np.isfinite(rm), rm, 0.0)
        A_repel = np.exp(rscore - rm) * mask
        rdenom = A_repel.sum(1, keepdims=True)
        A_repel = np.where(rdenom > 0, A_repel / np.where(rdenom > 0, rdenom, 1.0), 0.0)
        dirn = delta / np.sqrt(d2[..., None] + 1e-4)
        repel = np.einsum("ij,ijc->ic", A_repel, dirn)

        # complementary-fit attraction (kept, weak) — drives the induced-fit MORPH below
        score = np.where(mask, (S_comp - cfg.dist_lambda * d2) / tau, -np.inf)
        m = np.max(score, axis=1, keepdims=True)
        m = np.where(np.isfinite(m), m, 0.0)
        A_fit = np.exp(score - m) * mask
        denom = A_fit.sum(1, keepdims=True)
        A_fit = np.where(denom > 0, A_fit / np.where(denom > 0, denom, 1.0), 0.0)
        attract = -np.einsum("ij,ijc->ic", A_fit, delta)

        # THE NEW TERM: force from the contour-derived charges (protrusion + ↔ centre −)
        charge_force = self._charge_force()

        force = self.repel * repel + self.attract * attract + charge_force

        self.vel = self.momentum * self.vel + force
        sp = np.linalg.norm(self.vel, axis=1, keepdims=True)
        self.vel = np.where(sp > self.maxvel, self.vel * self.maxvel / (sp + 1e-9), self.vel)
        p = self.X[:, :POS_DIM] + self.speed * self.vel
        p = ((p + cfg.pos_bound) % self.L) - cfg.pos_bound

        # induced-fit morph (active tokens only) — pack.py's block; water stays round
        z = self.X[:, POS_DIM:]
        msg = A_fit @ (z @ self.W_v)
        spin = self.skew * (z @ self.J) if self.skew > 0 else 0.0
        z1 = _ln(z + self.morph * msg + spin)
        z2 = _ln(z1 + np.tanh(z1 @ self.W1 + self.b1) @ self.W2 + self.b2)
        z2[self.species == WATER, : self.tK] = 0.0           # freeze water's shape → round

        self.X = np.concatenate([p, z2], axis=1)
        self.t += 1

    def polarity(self):
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
        pol = self.polarity()
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
    pol = e.polarity()
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}" viewBox="0 0 {W} {W}">',
             f'<rect width="{W}" height="{W}" fill="#0e131b"/>']
    th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    K = e.cfg.n_harmonics
    for i in range(e.cfg.N):
        r = e.r0 * (1.0 + e.amp * sum(C[i, 2 * (k - 1)] * np.cos((k + 1) * th)
                                      + C[i, 2 * (k - 1) + 1] * np.sin((k + 1) * th) for k in range(1, K + 1)))
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
    e = PolarPackEngine(_cfg(), a.seed, water_frac=a.water, charge=a.charge, attract=a.attract)
    lip = e.species == ACTIVE
    print(" tick  polarity  clusters  largest  speed")
    for _ in range(0, a.ticks + 1, a.every):
        m = e.measure()
        speed = float(np.mean(np.linalg.norm(e.vel[lip], axis=1))) if lip.any() else 0.0
        print(f"{e.t:6d}   {m['polarity']:.3f}     {m['clusters']:3d}     {m['largest']:.3f}   {speed:.4f}")
        for _ in range(a.every):
            e.step()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--probe", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ticks", type=int, default=2000)
    p.add_argument("--every", type=int, default=400)
    p.add_argument("--water", type=float, default=0.4)
    p.add_argument("--charge", type=float, default=0.6)
    p.add_argument("--attract", type=float, default=0.15)
    p.add_argument("--out", default=None, help="render final frame to this SVG path")
    a = p.parse_args(argv)
    if a.out:
        e = PolarPackEngine(_cfg(), a.seed, water_frac=a.water, charge=a.charge, attract=a.attract)
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
