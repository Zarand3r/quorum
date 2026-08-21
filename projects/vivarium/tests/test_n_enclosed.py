"""n_enclosed must separate a single closed shell from a branched tangle.

This is the criterion that percolation could not supply. A finite branched network sits inside a
box larger than itself and so reports perc = n exactly as a vesicle does; only the number of
enclosed regions tells them apart. The dilution-quench aggregates scored 3-4 against the planted
vesicle's 1, and without this test that difference had no guard.

The shapes here are drawn directly, not simulated, so the test asserts geometry rather than physics.
"""

import numpy as np

from _lumen_field import lumen_cells, n_enclosed


def _ring(cx, cy, r, n):
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return np.stack([cx + r * np.cos(t), cy + r * np.sin(t)], axis=1)


def _as_mols(pts):
    return [np.arange(len(pts), dtype=np.int64)], pts


def test_single_ring_encloses_exactly_one_region():
    mols, X = _as_mols(_ring(30.0, 30.0, 10.0, 120))
    count, sizes = n_enclosed(X, mols, 60.0)
    assert count == 1, f"a closed ring must enclose one region, got {count} ({sizes})"


def test_theta_shape_encloses_two_regions():
    """A ring with a bar across it -- the simplest branched shape -- encloses two, not one."""
    ring = _ring(30.0, 30.0, 12.0, 160)
    bar = np.stack([np.full(24, 30.0), np.linspace(18.5, 41.5, 24)], axis=1)
    mols, X = _as_mols(np.concatenate([ring, bar]))
    count, sizes = n_enclosed(X, mols, 60.0)
    assert count == 2, f"a theta encloses two regions, got {count} ({sizes})"


def test_open_arc_encloses_nothing():
    t = np.linspace(0.0, 1.4 * np.pi, 100)
    arc = np.stack([30.0 + 12.0 * np.cos(t), 30.0 + 12.0 * np.sin(t)], axis=1)
    mols, X = _as_mols(arc)
    count, _ = n_enclosed(X, mols, 60.0)
    assert count == 0, f"an arc with a gap encloses nothing, got {count}"


def test_lumen_cells_is_the_largest_enclosed_region():
    """The refactor must not have changed lumen_cells: it is still max(sizes), or 0 below threshold."""
    ring = _ring(30.0, 30.0, 12.0, 160)
    bar = np.stack([np.full(24, 30.0), np.linspace(18.5, 41.5, 24)], axis=1)
    mols, X = _as_mols(np.concatenate([ring, bar]))
    _, sizes = n_enclosed(X, mols, 60.0)
    assert lumen_cells(X, mols, 60.0) == max(sizes)


def _ring_spaced(R, spacing, L):
    n = max(8, int(round(2.0 * np.pi * R / spacing)))
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return np.stack([L / 2 + R * np.cos(t), L / 2 + R * np.sin(t)], axis=1)


def test_vesicle_vs_tangle_call_survives_the_dilation_knob():
    """The COUNT moves with dilation; the 1-versus-many CALL must not.

    On real quench tangles the count runs 5/4/4/3 and 8/6/6/4 over bead 1.0-3.0 as thin necks seal
    and unseal. Only the call is reportable, so only the call is gated.
    """
    ring = _ring_spaced(43.0, 1.0, 120.0)
    # the crossbar must be built at the MEASURED membrane density (0.95 sigma nearest
    # neighbour); a sparse bar leaks at low dilation and the theta reads as a plain ring.
    bar = np.stack([np.full(90, 60.0), np.linspace(17.5, 102.5, 90)], axis=1)
    theta = np.concatenate([ring, bar])
    for bead in (1.0, 1.5, 2.0, 3.0):
        assert n_enclosed(ring, [np.arange(len(ring))], 120.0, bead=bead)[0] == 1, f"ring at bead {bead}"
        assert n_enclosed(theta, [np.arange(len(theta))], 120.0, bead=bead)[0] >= 2, f"theta at bead {bead}"


def test_genuine_opening_is_not_sealed_shut():
    """The opposite failure: dilating far enough to seal a real gap would invent lumens."""
    R, spacing = 43.0, 1.0
    for gap in (4.0, 6.0):
        n = int(round(2.0 * np.pi * R / spacing))
        frac = gap / (2.0 * np.pi * R)
        t = np.linspace(0.0, 2.0 * np.pi * (1.0 - frac), n)
        pts = np.stack([60.0 + R * np.cos(t), 60.0 + R * np.sin(t)], axis=1)
        count, _ = n_enclosed(pts, [np.arange(len(pts))], 120.0)
        assert count == 0, f"a {gap} sigma opening must read open, got {count}"


def test_vesicle_call_rejects_a_network_with_an_incidental_pocket():
    """Gate 2: a ring enclosing its own contour passes; a sprawling shape with a small hole does not.

    The pre-registered emergence criterion had only the n_enclosed==1 gate, and a 160-lipid branched
    network passed it with a lumen 0.028 of the size its own lipid count implies. The render caught
    that; the metric did not.
    """
    from _lumen_field import vesicle_call

    n = 160
    R = n / (2.0 * np.pi)
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    ring = np.stack([32.5 + R * np.cos(t), 32.5 + R * np.sin(t)], axis=1)
    ok, why = vesicle_call(ring, [np.arange(len(ring))], 65.0)
    assert ok, f"a closed ring of its own contour must be a vesicle: {why}"

    # a long meander that pinches off one small pocket: closed, but nowhere near its contour's area
    s = np.linspace(0.0, 1.0, n)
    snake = np.stack([6.0 + 52.0 * s, 32.5 + 9.0 * np.sin(9.0 * np.pi * s)], axis=1)
    ok2, why2 = vesicle_call(snake, [np.arange(len(snake))], 65.0)
    assert not ok2, f"a meander is not a vesicle, but passed: {why2}"


def test_shell_split_control_a_clean_ring_has_no_appendages():
    """Calibration control: a ring with nothing attached must be all shell.

    At reach 2.5 this returns 98/22 on a real planted vesicle because only the inner leaflet is
    within range; the reach has to span the bilayer. 5.0 is where the control comes out clean.
    """
    from _lumen_field import shell_split

    n = 160
    R = n / (2.0 * np.pi)
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    ring = np.stack([32.5 + R * np.cos(t), 32.5 + R * np.sin(t)], axis=1)
    mols = [np.array([i]) for i in range(len(ring))]
    shell, app, lumen = shell_split(ring, mols, 65.0)
    assert app == 0, f"a clean ring must have no appendages, got {app} (shell {shell})"
    assert shell == n and lumen > 0
