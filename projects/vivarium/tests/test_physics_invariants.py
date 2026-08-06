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


def _free_particle_rms(scale: float, steps: int) -> float:
    """RMS displacement of non-interacting lipids after `steps`, with `speed` scaled post-build.

    An ensemble statistic, not a trajectory comparison: rng_for() keys the draw on the step index, so
    two runs of different length never share a noise sequence and their positions are incomparable.
    """
    import numpy as np

    from bicelle2d import build

    e = build(3, n_lip=12, bound=8.0, kt=0.05, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
              attract=1.0, bond_span=2.0, n_tail=2, polarity=0.80, head_q=1.2,
              hydrophobic=0.6, n_water=40, plant=False)
    e.repel = e.attract = e.polarity = e.k_tail = e.k_hydro = e.k_bond = 0.0
    e.speed *= scale                       # exactly what the viewer's slider does; speed_ref unchanged
    e.vel[:] = 0.0
    start = e.X[:, :e.pd].copy()
    for _ in range(steps):
        e.step()
    d = e.X[:, :e.pd] - start
    d -= e.L * np.round(d / e.L)
    return float(np.sqrt((d ** 2).sum(axis=1).mean()))


def test_moving_the_speed_slider_does_not_change_thermal_motion() -> None:
    """Dragging `speed` must not change how much Brownian motion the dish gets.

    The kick is applied per STEP while drift is scaled by `speed`, so at matched physical time
    (N*speed fixed) the random walk carried a sqrt(speed) bias -- measured RMS ratio 2.12 against the
    predicted sqrt(4) = 2.0. The viewer advertised `speed` as "playback rate -- NOT physics" while it
    was in fact an effective-temperature dial.

    Fixed by rescaling the kick against a per-ENGINE reference captured at construction, so the factor
    is exactly 1 at an engine's configured speed and the correction applies only when speed MOVES.
    """
    slow, fast = _free_particle_rms(1.0, 400), _free_particle_rms(4.0, 100)   # same physical time
    ratio = fast / slow
    assert 1 / 1.3 <= ratio <= 1.3, (
        f"`speed` still changes thermal motion at fixed physical time: RMS ratio {ratio:.2f}, "
        f"expected ~1.0 (2.0 would be the unfixed langevin bias)")


def test_construction_speed_stays_bit_for_bit_reproducible() -> None:
    """The kick rescaling must be a no-op at an engine's own construction speed.

    Every result in this project was produced at a construction speed, so the fix is only admissible
    if those trajectories are untouched: speed_ref == speed there, making the factor exactly 1.0.
    """
    import numpy as np

    from bicelle2d import build

    kw = dict(n_lip=10, bound=8.0, kt=0.05, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
              attract=1.0, bond_span=2.0, n_tail=2, polarity=0.80, head_q=1.2, hydrophobic=0.6,
              n_water=30, plant=False)
    a, b = build(5, **kw), build(5, **kw)
    assert a.speed_ref == a.speed
    for _ in range(50):
        a.step()
        b.step()
    assert np.array_equal(a.X, b.X), "construction-speed trajectory is not reproducible"


def test_speed_fix_is_scoped_to_slider_moves_not_reconfiguration() -> None:
    """Documents what the fix does NOT do, so the limitation is recorded rather than assumed away.

    Two engines BUILT at different speeds each get speed_ref == their own speed, so each is its own
    baseline and the sqrt(speed) relationship between them survives. Making those equivalent needs a
    single global reference, which would rescale the noise of one engine family or the other -- they
    are constructed two orders of magnitude apart (0.001 here, 1.20 for the showcase). Construction
    speed is part of a configuration; the slider is not.
    """
    import numpy as np

    from bicelle2d import build

    def rms(speed: float, steps: int) -> float:
        e = build(3, n_lip=12, bound=8.0, kt=0.05, speed=speed, repel=12.0, k_bond=30.0, satt=0.30,
                  attract=1.0, bond_span=2.0, n_tail=2, polarity=0.80, head_q=1.2,
                  hydrophobic=0.6, n_water=40, plant=False)
        e.repel = e.attract = e.polarity = e.k_tail = e.k_hydro = e.k_bond = 0.0
        e.vel[:] = 0.0
        start = e.X[:, :e.pd].copy()
        for _ in range(steps):
            e.step()
        d = e.X[:, :e.pd] - start
        d -= e.L * np.round(d / e.L)
        return float(np.sqrt((d ** 2).sum(axis=1).mean()))

    ratio = rms(0.004, 100) / rms(0.001, 400)
    assert ratio > 1.3, (
        "constructing at a different speed is now speed-invariant too -- if that was intended, "
        "delete this test; if not, a global speed reference has crept in and one engine family's "
        "noise has been silently rescaled")
