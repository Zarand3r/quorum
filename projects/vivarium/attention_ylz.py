"""M2 of ROADMAP_V2: the YLZ energy written as a distance-penalized attention layer.

This is a CONSTRUCTION, not a fit. The claim is that the membrane potential which produces vesicles
(verified in M0 against stock LAMMPS, and in M1 in our own engine) is already expressible with the
primitives of geometric attention, with no approximation at all.

The identity that makes it work:

    n_i . n_j - (n_i.r_hat)(n_j.r_hat)  ==  n_i^T (I - r_hat r_hat^T) n_j

The left side is YLZ's angular term. The right side is a query-key inner product under a metric that
depends only on the pair's relative direction -- exactly what relative-position-aware attention
computes. Writing the full potential in the form

    U(r, n_i, n_j) = A(r) + B(r) * a_ij

    a_ij = <q_i, k_j> - p_i p_j + beta (p_i - p_j) - beta^2
    q_i  = W_q n_i,  k_j = W_k n_j,  p_i = <W_p n_i, r_hat>

separates it cleanly into a RADIAL GATE (A, B: scalar functions of distance, i.e. the distance
penalty) and a CONTENT term built from inner products between per-token vectors. Collecting the two
branches of the piecewise potential:

    r <  r_min :  U = u_R + (1 - phi) eps  = [u_R + mu eps]      + [-mu eps] a
    r >= r_min :  U = u_A phi              = [u_A (1 - mu)]      + [mu u_A]  a

so A and B are just those bracketed radial functions.

At construction W_q = W_k = W_p = I and A, B are the exact analytic radial functions, which makes the
energy identical to `ylz.energy()` to machine precision. That is the point: M2 establishes
EXPRESSIBILITY exactly, so that when M3 replaces the radial functions with a learned basis or the
projections with learned matrices, any loss of vesiculation is attributable to that specific
substitution and nothing else.

Note on normalisation. The attention here is UNNORMALIZED (no softmax over neighbours). That is
deliberate and load-bearing: softmax would make each pair's contribution depend on how many other
neighbours a particle has, destroying pairwise additivity, which this potential relies on. SPEC.md
asks for "local attention ... distance-penalized" and does not mandate softmax. Whether vesiculation
survives softmax normalisation is a separate experiment, and is the substitution most likely to break
the physics.
"""

from __future__ import annotations

import numpy as np

from ylz import YLZ, cell_pairs


class AttentionYLZ:
    """YLZ as one unnormalized, distance-penalized attention layer over (position, orientation).

    Parameters mirror `ylz.YLZ`. The projection matrices are explicit so that M3 can replace them
    with learned ones one at a time.
    """

    def __init__(self, ref: YLZ, W_q=None, W_k=None, W_p=None):
        self.ref = ref
        self.W_q = np.eye(3) if W_q is None else np.asarray(W_q, float)
        self.W_k = np.eye(3) if W_k is None else np.asarray(W_k, float)
        self.W_p = np.eye(3) if W_p is None else np.asarray(W_p, float)

    def radial_gate(self, r):
        """A(r), B(r): the distance penalty. Everything orientation-dependent lives in B's partner."""
        s = self.ref
        rmin, rc, eps, mu, zeta = s.rmin, s.rc, s.eps, s.mu, s.zeta
        uR = eps * ((rmin / r) ** 4 - 2.0 * (rmin / r) ** 2)
        arg = 0.5 * np.pi * (r - rmin) / (rc - rmin)
        uA = -eps * np.cos(arg) ** (2 * zeta)
        near = r < rmin
        A = np.where(near, uR + mu * eps, uA * (1.0 - mu))
        B = np.where(near, -mu * eps, mu * uA)
        return A, B

    def energy(self, x=None, nhat=None):
        s = self.ref
        x = s.x if x is None else x
        nhat = s.nhat if nhat is None else nhat
        L = s.L

        i, j = cell_pairs(x, L, s.rc)
        if not len(i):
            return 0.0
        rij = x[i] - x[j]
        rij -= L * np.round(rij / L)
        r = np.linalg.norm(rij, axis=1)
        m = (r < s.rc) & (r > 1e-9)
        i, j, rij, r = i[m], j[m], rij[m], r[m]
        if not len(i):
            return 0.0
        rhat = rij / r[:, None]

        # attention primitives: queries, keys, and direction-projected values
        q = nhat @ self.W_q.T
        k = nhat @ self.W_k.T
        pv = nhat @ self.W_p.T
        content = np.einsum("ic,ic->i", q[i], k[j])              # <q_i, k_j>
        p_i = np.einsum("ic,ic->i", pv[i], rhat)                 # projection on the pair direction
        p_j = np.einsum("ic,ic->i", pv[j], rhat)

        a = content - p_i * p_j + s.beta * (p_i - p_j) - s.beta ** 2
        A, B = self.radial_gate(r)
        return float((A + B * a).sum())


def check_identity(seed=0, n_part=200, L=12.0, trials=5):
    """Attention-form energy against the direct YLZ energy. Must agree to machine precision."""
    worst = 0.0
    for t in range(trials):
        s = YLZ(n_part, L, seed=seed + t, beta=0.1 + 0.05 * t)
        att = AttentionYLZ(s)
        e_direct, e_attn = s.energy(), att.energy()
        denom = max(abs(e_direct), 1e-12)
        worst = max(worst, abs(e_direct - e_attn) / denom)
    return worst


if __name__ == "__main__":
    rel = check_identity()
    print(f"max relative |E_attention - E_ylz| over 5 random systems = {rel:.3e}")
    print("PASS: YLZ is exactly one unnormalized distance-penalized attention layer"
          if rel < 1e-12 else "*** IDENTITY FAILED ***")
