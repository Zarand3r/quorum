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


def test_species_pair_repulsion_is_off_by_default_and_stays_reciprocal() -> None:
    """`repel_pair` must be a no-op when unset, and must not break Newton's third law when set.

    A single global `repel` cannot serve both the solvent and the membrane: repel 12 gives
    bilayer_frac 0.746 with the solvent collapsed to 0.43 of contact, repel 24 gives bulk water and no
    membrane. A species-pair matrix decouples them, exactly as `eps_pair` already does for cohesion.

    The matrix must be SYMMETRIC. An asymmetric one would make F_ij != -F_ji, and the whole system
    would accelerate under its own internal forces -- a failure no structural metric would reveal.
    """
    import numpy as np

    from bicelle2d import build

    kw = dict(n_lip=14, bound=8.0, kt=0.0, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
              attract=1.0, bond_span=2.0, n_tail=2, polarity=0.80, head_q=1.2, hydrophobic=0.6,
              n_water=60, plant=False)

    a, b = build(5, **kw), build(5, **kw)
    b.repel_pair = np.ones((7, 7))                    # all-ones must reproduce the global scale
    for _ in range(80):
        a.step()
        b.step()
    assert np.array_equal(a.X, b.X), "repel_pair = ones is not a no-op"

    c = build(5, **kw)
    m = np.ones((7, 7))
    m[0, 0] = 2.0                                     # stiffen water-water only
    c.repel_pair = m
    assert np.allclose(m, m.T), "the matrix under test must be symmetric"
    c.temperature = 0.0
    for _ in range(200):
        c.step()
    drift = float(np.linalg.norm(c.vel.sum(axis=0)) / len(c.vel))
    assert drift < 1e-9, f"species-pair repulsion broke reciprocity: net momentum {drift:.2e}"


def test_dpd_cell_list_matches_bruteforce() -> None:
    """The cell list must find exactly the pairs the O(N^2) search finds.

    A missed pair is a silently weaker force law, and at the densities used here it would look like a
    softer fluid rather than a bug -- precisely the kind of error this project keeps paying for.
    """
    import numpy as np

    from dpd_reference import DPD

    d = DPD(300, 8.7, kT=1.0, a=25.0, seed=7)
    for _ in range(20):
        d.step()
    i, j, _, _ = d._pairs()
    bi, bj = d.pairs_bruteforce()
    got = {(min(a, b), max(a, b)) for a, b in zip(i.tolist(), j.tolist())}
    want = {(min(a, b), max(a, b)) for a, b in zip(bi.tolist(), bj.tolist())}
    assert got == want, (
        f"cell list disagrees with brute force: {len(want - got)} missed, {len(got - want)} spurious")


def test_dpd_3d_cell_list_and_thermostat() -> None:
    """The 3-D path must find the same pairs as brute force and hold the target temperature.

    3-D is where the open-source DPD vesicle literature lives (DECISIONS.md D7). A missed pair or a
    mis-scaled thermostat in 3-D would look like "vesicles do not form here" rather than like a bug --
    the exact confusion this project has paid for repeatedly.
    """
    import numpy as np

    from dpd_reference import DPD

    d = DPD(400, 5.2, kT=1.0, a=25.0, seed=3, dim=3)
    for _ in range(30):
        d.step()
    i, j, _, _ = d._pairs()
    bi, bj = d.pairs_bruteforce()
    got = {(min(a, b), max(a, b)) for a, b in zip(i.tolist(), j.tolist())}
    want = {(min(a, b), max(a, b)) for a, b in zip(bi.tolist(), bj.tolist())}
    assert got == want, f"3-D cell list disagrees: {len(want - got)} missed, {len(got - want)} spurious"
    for _ in range(400):
        d.step()
    T = d.temperature()
    assert abs(T - 1.0) < 0.12, f"3-D thermostat off target: T={T:.3f} vs 1.0"


def test_dpd_bending_conserves_momentum_and_straightens_chains() -> None:
    """The three-body bending term must be internal (zero net force) and prefer straight chains.

    Published DPD membrane models stiffen the tails with an angle potential; without it, fully
    flexible chains coil rather than pack into leaflets. A bending term that leaked net force would
    accelerate the whole system, which no structural metric would catch.
    """
    import numpy as np

    from dpd_reference import DPD

    # a=0 and kT=0: ONLY the bending term acts. An earlier version of this test left repulsion and
    # 57 other beads switched on, so the angle moved for reasons that had nothing to do with bending.
    # a=0, kT=0, and BONDED: only bending plus the backbone acts. Without bonds three free beads
    # under an angle force alone are unconstrained and drift, which made an earlier version of this
    # test unreadable.
    d = DPD(3, 20.0, kT=0.0, a=0.0, seed=1, dim=3,
            bonds=np.array([[0, 1], [1, 2]]), k_bond=100.0, r0=1.0)
    d.angles = np.array([[0, 1, 2]])
    d.k_ang = 15.0
    d.x[0] = [2.0, 3.0, 3.0]
    d.x[1] = [3.0, 3.0, 3.0]
    d.x[2] = [3.6, 3.8, 3.0]            # bent
    f, _ = d.forces(with_dissipative=False)
    net = np.abs(f.sum(axis=0)).max()
    assert net < 1e-9, f"bending leaks net force: {net:.2e}"

    def angle(e):
        r1 = e.x[0] - e.x[1]; r2 = e.x[2] - e.x[1]
        c = float(r1 @ r2 / (np.linalg.norm(r1) * np.linalg.norm(r2)))
        return np.degrees(np.arccos(np.clip(c, -1, 1)))

    before = angle(d)
    for _ in range(300):
        d.step()
    assert angle(d) > before, f"bending did not straighten the chain: {before:.0f} -> {angle(d):.0f} deg"
