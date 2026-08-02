"""Fundamental physics invariants, tested rather than asserted in a docstring.

The force code CLAIMS to be conservative ("symmetric by construction, so the repulsion stays
conservative") and to use only bounded kernels. Those are the properties the whole model rests on,
and nothing checked them. Every one of these is a property of the PHYSICS, not of a metric, so a
violation would corrupt every result regardless of how well the measurement side behaves.
"""
import numpy as np
import pytest

from bicelle2d import build as build2d
from bilayer3d import build as build3d

KW2 = dict(n_lip=20, bound=8.0, kt=0.0, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
           n_tail=2, attract=1.0, bond_span=2.0, n_water=60, polarity=0.80, head_q=1.2,
           hydrophobic=0.6)
KW3 = dict(n_lip=16, bound=4.0, kt=0.0, speed=0.001, repel=12.0, k_bond=30.0, satt=0.55,
           spol=0.90, attract=1.0, polarity=0.80, head_q=1.2, n_tail=2, bond_span=2.0)


def _engines():
    yield "2-D", build2d(0, plant=False, **KW2)
    yield "3-D", build3d(0, plant=False, **KW3)


def test_no_net_drift_newtons_third_law():
    """Total momentum must not grow: internal forces cancel pairwise.

    If the pair forces were asymmetric the whole system would accelerate through the box under its
    own internal interactions -- a violation of Newton's third law that no structural metric would
    ever reveal, because every relative position stays plausible while the aggregate drifts.
    """
    for label, e in _engines():
        e.temperature = 0.0                     # no thermal noise: any drift is from the forces
        for _ in range(200):
            e.step()
        drift = float(np.linalg.norm(e.vel.sum(axis=0)) / len(e.vel))
        assert drift < 1e-9, f"{label}: net momentum per token {drift:.2e}, forces are not symmetric"


def test_forces_are_bounded_no_divergent_kernel():
    """Transformer-only forbids a 1/d^2-style kernel: every force must stay finite as d -> 0.

    Two tokens are driven onto ALMOST the same point, which is exactly where a divergent kernel blows
    up and a bounded (attention) one saturates.
    """
    for label, e in _engines():
        e.temperature = 0.0
        e.X[1, :e.pd] = e.X[0, :e.pd] + 1e-6    # nearly coincident
        for _ in range(5):
            e.step()
        assert np.all(np.isfinite(e.X)), f"{label}: non-finite positions"
        assert np.all(np.isfinite(e.vel)), f"{label}: non-finite velocities"
        assert float(np.abs(e.vel).max()) < 1e3, f"{label}: force blew up at contact"


def test_token_count_is_fixed():
    """A fixed token count is a hard constraint of the model: nothing is created or destroyed."""
    for label, e in _engines():
        n0 = len(e.X)
        for _ in range(100):
            e.step()
        assert len(e.X) == n0, f"{label}: token count changed {n0} -> {len(e.X)}"


def test_periodic_wrap_preserves_relative_geometry():
    """Wrapping is a relabelling, not a physical event.

    A configuration and the same configuration translated by a full box period must evolve
    identically. If wrapping leaked into the dynamics, results would depend on where the aggregate
    happened to sit -- and this project has already been burnt by geometry computed on raw
    coordinates.
    """
    for label, e in _engines():
        e.temperature = 0.0
        shifted = build2d(0, plant=False, **KW2) if label == "2-D" else build3d(0, plant=False, **KW3)
        shifted.temperature = 0.0
        L = 2 * e.cfg.pos_bound
        shifted.X[:, :e.pd] += L                 # translate by exactly one period
        for _ in range(50):
            e.step(); shifted.step()
        d = e.X[:, :e.pd] - shifted.X[:, :e.pd]
        d -= L * np.round(d / L)
        assert float(np.abs(d).max()) < 1e-8, f"{label}: wrapping changed the trajectory"
