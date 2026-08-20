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
