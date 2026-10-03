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

from field import _core, _core_derivative, _well, _well_derivative


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
        # Keep the Field's pair arrays rather than stacking them into a new (2, M) allocation. This
        # also lets `_env` reuse the fixed QK and size values cached for this exact neighbour mask.
        return iu, sep, dist

    def _spring_pairs(self, X, pairs):
        sep = X[pairs[:, 0]] - X[pairs[:, 1]]
        sep -= self.f.L * np.round(sep / self.f.L)
        return np.asarray([pairs[:, 0], pairs[:, 1]]), sep, np.linalg.norm(sep, axis=1)

    # ---- scores ------------------------------------------------------------------------------

    def _score_nonbonded(self, r, pairs):
        """a(r) + b(r) * (q_i . k_j), zeroed beyond the cutoff exactly as `field.forces` does.

        NO LONGER TRUE, and left here as the correction rather than deleted: chi is read from
        `field._env`, NOT from the token channel. `q()` and `k()` have no caller outside the tests, so
        `self.h` does not reach the forces and the MLP below cannot change interactions by changing it.
        `tests/test_transformer.py::test_qk_equals_the_chi_table` still pins q.k == the table to 1e-12,
        so the FORMULATION claim holds; the WIRING claim does not. This was introduced by decf88c5
        (2026-09-09) -- the commit that fixed two force paths disagreeing -- and is tracked as a red
        test in SUMMARY.md. Do not "fix" it by weakening the test: routing chi through q.k would change
        production trajectories at the eigendecomposition round-trip level, and that is a decision
        about what the project claims, not a cleanup.

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
        # ONE source of truth for sigma and chi: `field._env`. Both are configuration-dependent once
        # a shape or affinity modulator is attached, and `transformer.attention` is a SECOND
        # implementation of the same force law -- on 2026-09-09 the many-body term went into
        # `field.forces` only, so both G4 arms were the same simulation
        # (max|X_off - X_mlp| = 0.000e+00). Recomputing sigma here from `pair_sigma`, which is
        # per-SPECIES, would repeat that with the shape channel, which is per-BEAD.
        sig, chi, extra = f._env(r, pairs)
        s = r / sig
        duc = _core_derivative(s, f.core_height)
        if extra is None:
            uw = None
            duw = _well_derivative(s, f.rc)
        else:
            uw, duw = _well(s, f.rc)
        self._mb = None
        if extra is not None:
            self._mb = (extra, uw, s, sig, r, pairs)
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
        if getattr(self, "_mb", None) is not None:
            # dU/dq . dq/dn . dn/dx for every modulated quantity, matching field.forces exactly.
            from _scatter import scatter_add, scatter_add_pair
            (chi0, fx, dfx, dsb, dw, both), uw, sr, sig, r, pr = self._mb
            n = len(X)
            _, duc2 = _core(sr, self.f.core_height)
            _, duw2 = _well(sr, self.f.rc)
            chi_mod = chi0 * (fx[pr[0]] * fx[pr[1]] if fx is not None else 1.0)
            dudr = self.f.eps * (duc2 + duw2 * chi_mod) / sig
            dudr = np.where(r < self.f.rc * sig, dudr, 0.0)
            safe = np.maximum(r, 1e-12)
            chain = np.zeros(n)
            if fx is not None:
                g = self.f.eps * uw * chi0
                chain = chain + (scatter_add(n, pr[0], g * fx[pr[1]])
                                 + scatter_add(n, pr[1], g * fx[pr[0]])) * dfx
            if dsb is not None:
                half = -0.5 * sr * dudr
                chain = chain + (scatter_add(n, pr[0], half)
                                 + scatter_add(n, pr[1], half)) * dsb
            cm = np.where(both, (chain[pr[0]] + chain[pr[1]]) * dw / safe, 0.0)
            out -= scatter_add_pair(n, pr[0], pr[1], cm[:, None] * sep)
        for sp, k, r0 in self.f._springs():
            p, sep, dist = self._spring_pairs(X, sp)
            out += AttentionHead("spring", self._score_spring(k, r0))(X, self.f.L, p, sep, dist)
        if self.f.k_theta > 0.0 and len(self.f.triples):
            out += self._angle_head(X)
        return out

    def _angle_head(self, X):
        """The bending term as a TWO-PASS masked operation: gather at the centre, scatter to the ends.

        An angle is irreducibly three-body and a single attention head is pairwise, so this cannot be
        one head. It is the same shape as the many-body term above, which is already in this file and
        already in the production path: accumulate a per-bead quantity from a masked neighbourhood,
        then redistribute it. Here pass 1 gathers the two bond vectors at the centre bead j, pass 2
        scatters the resulting force to i, j and k.

        REIMPLEMENTED, not delegated to `field._angle_forces`. That is the convention in this file --
        the springs and the many-body term are both written out again here -- because the point of
        `test_physical_realism`'s cross-path gate is that two INDEPENDENT routes agree. Calling
        field's version would make that gate unfalsifiable.
        """
        from _scatter import scatter_add
        t = self.f.triples
        L = self.f.L
        u = X[t[:, 0]] - X[t[:, 1]]
        v = X[t[:, 2]] - X[t[:, 1]]
        u -= L * np.round(u / L)
        v -= L * np.round(v / L)
        nu = np.maximum(np.linalg.norm(u, axis=1), 1e-12)
        nv = np.maximum(np.linalg.norm(v, axis=1), 1e-12)
        cos = np.clip((u * v).sum(axis=1) / (nu * nv), -1.0, 1.0)
        phi = np.pi - np.arccos(cos)
        # 1/sin(theta) is harmless at theta = pi (sin evaluates to 1.22e-16, phi is 0, and the
        # geometric factor vanishes) but is a true NaN at theta = 0, a chain folded onto itself.
        ratio = -phi / np.maximum(np.sin(np.arccos(cos)), 1e-12)
        pref = self.f.k_theta * ratio
        fi = pref[:, None] * (v / (nu * nv)[:, None] - (cos / (nu * nu))[:, None] * u)
        fk = pref[:, None] * (u / (nu * nv)[:, None] - (cos / (nv * nv))[:, None] * v)
        n = len(X)
        out = np.zeros_like(X)
        for col, f in ((0, fi), (2, fk), (1, -(fi + fk))):
            for dim in range(X.shape[1]):
                out[:, dim] += scatter_add(n, t[:, col], f[:, dim])
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
