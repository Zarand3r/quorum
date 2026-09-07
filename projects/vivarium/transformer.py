"""The simulation step as a transformer forward pass.

The design constraint this file exists to satisfy: the dynamics must be expressible with attention and
MLP blocks only, one forward pass per simulation step, with no separate training phase.

WHAT WAS ALREADY TRUE. The non-bonded force in `field.py` is

    F_i = sum_j  -(1/r_ij) * dU/dr_ij * (x_i - x_j)
        = sum_j  [ a(r_ij) + b(r_ij) * (q_i . k_j) ] * (x_i - x_j)

with a(r) = -(eps/sigma) * core'(r/sigma) / r and b(r) = -(eps/sigma) * well'(r/sigma) / r. That is a
scalar attention score -- a query-key inner product modulated by a distance function, plus a
distance-only bias -- applied to relative-position values. Unnormalised, and equivariant because the
values are differences of positions rather than positions.

WHAT WAS NOT. The harmonic bonds and the 1-3 stiffener were computed by a separate loop outside that
form, and there was no MLP anywhere. Both are addressed here: a spring is the same score-times-relative-
position shape restricted to a pair mask, which is masked attention, and the hidden state carried by
each token is what an MLP acts on.

The head decomposition is exact, not approximate. `test_transformer_reproduces_field_forces` asserts
agreement with `field.forces()` to 1e-12 on a system exercising every head.
"""

import numpy as np

from _scatter import scatter_add, scatter_add_pair

from field import _core, _well


class AttentionHead:
    """One head: a scalar score per pair, applied to relative-position values.

    `score(r, pairs)` returns the per-pair scalar. `mask` selects which pairs the head sees. Every force
    in this model is of this shape; the heads differ only in their score function and their mask.
    """

    def __init__(self, name, score_fn):
        self.name = name
        self.score_fn = score_fn

    def __call__(self, X, L, pairs, sep, dist):
        s = self.score_fn(dist, pairs)
        contrib = s[:, None] * sep
        return scatter_add_pair(len(X), pairs[0], pairs[1], contrib)


class VivariumTransformer:
    """Wraps a Field and reproduces its forces as a sum of masked attention heads.

    Heads:
      * `nonbonded` -- mask is the neighbour list, score is a(r) + b(r) * (q_i . k_j)
      * `bond`      -- mask is the 1-2 adjacency, score is -k (r - r0) / r
      * `angle`     -- mask is the 1-3 adjacency, same score with the bend constants

    The token state is (x, v, h): position and velocity are equivariant, h is invariant. h is unused in
    this slice and exists so the MLP block has something to act on; with h fixed the dynamics is
    identical to the pre-existing integrator, which is what makes the change verifiable.
    """

    def __init__(self, field, mlp_width=8):
        self.f = field
        self.mlp_width = int(mlp_width)
        self.h = None                       # invariant per-token channel, set by reset()
        self.reset()

    # ---- masks -------------------------------------------------------------------------------

    def _nonbonded_pairs(self, X):
        sep, dist, iu = self.f._pairs(X)
        return np.asarray(iu), sep, dist

    def _spring_pairs(self, X, pairs):
        sep = X[pairs[:, 0]] - X[pairs[:, 1]]
        sep -= self.f.L * np.round(sep / self.f.L)
        return np.asarray([pairs[:, 0], pairs[:, 1]]), sep, np.linalg.norm(sep, axis=1)

    # ---- scores ------------------------------------------------------------------------------

    def _score_nonbonded(self, r, pairs):
        """a(r) + b(r) * (q_i . k_j), zeroed beyond the cutoff exactly as `field.forces` does.

        The query and key come from the TOKEN CHANNEL h, not from a species lookup: q_i = h_i W_q and
        k_i = h_i W_k. With h the one-hot species this is algebraically identical to the original
        `content_pairs`, which is what lets the MLP below change interactions without changing anything
        else.

        a(r) and b(r) stay analytic. They are a fixed distance-dependent bias inside the attention
        score -- the same role ALiBi plays in a language model -- and that is a transformer component
        already. Replacing them with an MLP of r was considered and rejected: core' is exactly one ReLU
        unit, but well' is sinusoidal and both carry a 1/r factor, so an MLP could only approximate
        them. That would trade an exact force law for architectural box-ticking.
        """
        f = self.f
        # `f.pair_sigma` is the SAME helper `field.forces` uses, deliberately. Per-species bead size
        # enters the radial gate, so a second copy of the Lorentz rule here would be a place for the
        # attention identity to drift away from the force law without any test noticing.
        sig = f.pair_sigma(*pairs)
        s = r / sig
        _, duc = _core(s, f.core_height)
        _, duw = _well(s, f.rc)
        chi = np.einsum("ic,ic->i", self.q()[pairs[0]], self.k()[pairs[1]])
        dudr = f.eps * (duc + duw * chi) / sig
        dudr = np.where(r < f.rc * sig, dudr, 0.0)
        return -dudr / np.maximum(r, 1e-12)

    def q(self):
        return self.h @ self.Wq

    def k(self):
        return self.h @ self.Wk

    @staticmethod
    def _score_spring(k, r0):
        def fn(r, pairs):
            return -k * (r - r0) / np.maximum(r, 1e-12)
        return fn

    # ---- the attention block -----------------------------------------------------------------

    def attention(self, X):
        """Sum of the masked heads. Equals `field.forces(X)` exactly."""
        out = np.zeros_like(X)
        pairs, sep, dist = self._nonbonded_pairs(X)
        out += AttentionHead("nonbonded", self._score_nonbonded)(X, self.f.L, pairs, sep, dist)
        for sp, k, r0 in self.f._springs():
            p, sep, dist = self._spring_pairs(X, sp)
            out += AttentionHead("spring", self._score_spring(k, r0))(X, self.f.L, p, sep, dist)
        return out

    # ---- forward pass ------------------------------------------------------------------------

    def reset(self):
        """Initialise the token channel and the projections that read it.

        h starts as the one-hot species, and Wq/Wk are the eigendecomposition factors the Field already
        uses, so q_i . k_j reproduces chi exactly. The MLP starts at zero, so the first forward pass is
        bit-identical to the pre-existing integrator -- that identity is the regression gate for
        everything built on top.
        """
        sp = np.asarray(self.f.species)
        self.h = np.eye(len(self.f.q))[sp]        # one-hot species, (n, N_SPECIES)
        self.Wq = np.asarray(self.f.q)            # (N_SPECIES, C)
        self.Wk = np.asarray(self.f.k)
        self.W1 = np.zeros((self.h.shape[1] + 1, self.mlp_width))
        self.W2 = np.zeros((self.mlp_width, self.h.shape[1]))

    def mlp(self, X, pairs, sep, dist, scores):
        """Per-token MLP on the invariant channel.

        Its input is h and one invariant message per token -- the summed attention score, which is a
        rotation-invariant summary of the neighbourhood. Output is a residual on h, so with W2 = 0 the
        channel is frozen and the dynamics is unchanged. This is where an MLP can act without
        approximating anything, unlike the radial functions.
        """
        m = (scatter_add(len(X), pairs[0], scores)
             + scatter_add(len(X), pairs[1], scores))
        z = np.concatenate([self.h, m[:, None]], axis=1)
        return np.maximum(z @ self.W1, 0.0) @ self.W2

    def forward(self, X, v, dt, kT, gamma=1.0, mass=1.0, rng=None, F=None):
        """One simulation step as one forward pass.

        Velocity Verlet with an exact OU thermostat, written so that the only interaction term is the
        attention block. Returns (X, v, F) so the caller can carry the force across the step boundary,
        which is what makes it one attention evaluation per step rather than two.
        """
        if F is None:
            F = self.attention(X)
        v = v + 0.5 * dt * F / mass
        X = X + dt * v
        X = X - self.f.L * np.round(X / self.f.L)
        F = self.attention(X)
        v = v + 0.5 * dt * F / mass
        c1 = np.exp(-gamma * dt)
        v = c1 * v + np.sqrt(kT / mass * (1.0 - c1 * c1)) * rng.normal(size=X.shape)
        return X, v, F
