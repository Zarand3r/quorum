"""Known-answer tests for every structural metric.

The rule this project learned the expensive way: a metric is worthless until it is checked against a
structure whose answer is fixed BY CONSTRUCTION, and the check must be able to FAIL. Judging by
scalars alone produced six retracted claims; every single time an image or a raw profile was
consulted, it contradicted the scalar.

So each metric is pinned here against synthetic geometry built by hand, where the correct value is
known before the code runs. These are not regression tests on today's numbers -- they are assertions
about what the metrics MEAN. Bugs already caught by exactly this method:

  * largest_cluster connected molecules by their MIDDLE bead, so it split every bilayer into two
    leaflets, cluster_frac read 0.50, and the harness DISQUALIFIED a perfect bilayer as "fragmented".
  * the planted bilayer control at bound=5 with 4-bead tails spans 9 of a 10 box, so its two head
    layers were 1.0 apart ACROSS the periodic boundary: the reference itself was invalid.
"""

import numpy as np
import pytest

from config import DEFAULTS, VivariumConfig
from harness import largest_cluster, measure
from polar_pack import PolarPackEngine


def _engine(n_lip, n_tail, bound):
    nb = 1 + n_tail
    cfg = VivariumConfig(**{**DEFAULTS, "N": nb * n_lip, "pos_dim": 3, "n_harmonics": 2,
                            "pos_bound": bound})
    e = PolarPackEngine(cfg, 0, water_frac=0.0, chain_frac=1.0, polarity=0.0, repel=12.0,
                        n_tail=n_tail, rad_head=0.0, head_q=0.0, bond_span=2.0, aniso=0.0)
    e.wall_axes = ()
    return e


def _place_bilayer(e, gap=1.0):
    """Two leaflets, heads out, tails meeting at the midplane. Answer known by construction."""
    mol = e._mol
    nb = mol.shape[1]
    per = len(mol) // 2
    k = int(np.ceil(np.sqrt(per)))
    B = e.cfg.pos_bound
    xs = (np.arange(k) + 0.5) / k * 2 * B - B
    gx, gy = np.meshgrid(xs, xs, indexing="ij")
    flat = np.stack([gx.ravel(), gy.ravel()], axis=1)
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        pts = flat[:len(idx)]
        for bead in range(nb):
            off = gap / 2 + (nb - 1 - bead) * 1.0
            e.X[idx[:, bead], 0] = pts[:, 0]
            e.X[idx[:, bead], 1] = pts[:, 1]
            e.X[idx[:, bead], 2] = sgn * off
    e.vel[:] = 0.0


def test_bilayer_is_one_cluster_not_two_leaflets():
    """A bilayer's leaflets meet tail-to-tail, so it is ONE aggregate.

    largest_cluster used to connect on the MIDDLE bead, whose leaflet separation is ~5, and split
    every bilayer in half -- which made the harness reject the target structure as fragmented.
    """
    # bound = k/2 gives unit lateral spacing; at bound=6 with 8 columns the spacing is 1.5 and the
    # lipids are not in contact, which is a broken REFERENCE rather than a clustering failure.
    k = int(np.ceil(np.sqrt(128 // 2)))
    e = _engine(n_lip=128, n_tail=2, bound=k / 2.0)
    _place_bilayer(e)
    comp = largest_cluster(e)
    assert len(comp) == len(e._mol), f"bilayer split into {len(comp)}/{len(e._mol)} molecules"


def test_planted_bilayer_fits_inside_the_box():
    """A reference must not span its own periodic box, or its two faces touch across the boundary.

    At bound=5 with 4-bead tails the planted bilayer is ~9 thick in a box of 10: the head layers sat
    1.0 apart through the wrap, and every metric calibrated on it was meaningless.
    """
    for n_tail, bound in ((2, 6.0), (4, 9.0)):
        e = _engine(n_lip=64, n_tail=n_tail, bound=bound)
        _place_bilayer(e)
        z = e.X[e._mol.ravel(), 2]
        span = float(z.max() - z.min())
        gap = 2 * bound - span
        assert gap > 2.0, (f"n_tail={n_tail}: structure spans {span:.1f} of a {2*bound:.0f} box, "
                           f"leaving only {gap:.1f} across the wrap")


def test_bilayer_scores_as_flat_and_ordered():
    """The metrics must actually recognise a bilayer: lamellar ~1, aspect low, one cluster."""
    k = int(np.ceil(np.sqrt(128 // 2)))
    e = _engine(n_lip=128, n_tail=2, bound=k / 2.0)
    _place_bilayer(e)
    m = measure(e)
    assert m["ok"], f"a perfect bilayer was disqualified: {m['why']}"
    assert m["align"] > 0.90, f"align={m['align']:.3f} on a perfect bilayer (axes must share a normal)"
    assert m["aspect"] < 0.45, f"aspect={m['aspect']:.3f} on a perfect bilayer (should be thin)"
    assert m["cluster_frac"] > 0.95, f"cluster_frac={m['cluster_frac']:.2f}"


def test_random_configuration_scores_at_the_null():
    """A random configuration must NOT look ordered. Without this the scale has no zero."""
    e = _engine(n_lip=128, n_tail=2, bound=6.0)
    rng = np.random.default_rng(0)
    B = e.cfg.pos_bound
    mol = e._mol
    cen = rng.uniform(-B, B, (len(mol), 3))
    ax = rng.standard_normal((len(mol), 3))
    ax /= np.linalg.norm(ax, axis=1, keepdims=True)
    for b in range(mol.shape[1]):
        e.X[mol[:, b], :3] = cen + (1.0 - b) * ax
    m = measure(e)
    assert m["lamellar"] < 0.75, f"random config scored lamellar={m['lamellar']:.3f}"


def test_deformed_molecule_is_refused_not_scored():
    """A torn molecule must DISQUALIFY. Structural metrics on a broken molecule describe nothing."""
    e = _engine(n_lip=64, n_tail=2, bound=6.0)
    _place_bilayer(e)
    e.X[e._mol[:, 1], 0] += 3.0            # tear every first bond
    m = measure(e)
    assert not m["ok"] and "deformed" in m["why"], f"torn molecule was scored: {m}"


def test_packing_passes_a_known_good_bilayer_and_fails_a_collapse():
    """The guard that was missing for fifteen defects: matter must occupy space.

    Calibrated against both ends, because a threshold validated only against failures will happily
    reject every good structure too. The 3-D planted bilayer's lipids sit at EXACTLY contact.
    """
    from bilayer3d import build as build3d
    from harness import MIN_PACKING, measure, packing

    good = build3d(seed=1, n_lip=48, bound=3.4, kt=0.02, speed=0.08, repel=12.0,
                   k_bond=8.0, satt=0.55, spol=0.90, plant=True)
    assert packing(good) > 0.95, "a planted bilayer's lipids sit at contact; anything less is a bug"
    assert measure(good)["ok"], "the guard must not reject a known-good structure"

    # A collapse is invisible to every other guard here: bonds are INTRAMOLECULAR so each stacked
    # molecule reports a perfect 1.0, direction-based metrics stay well defined at any density, and
    # a collapsed pile is maximally connected so cluster_frac reads its BEST value.
    collapsed = build3d(seed=1, n_lip=48, bound=3.4, kt=0.02, speed=0.08, repel=12.0,
                        k_bond=8.0, satt=0.55, spol=0.90, plant=True)
    collapsed.X[:, :collapsed.pd] *= 0.15
    m = measure(collapsed)
    assert packing(collapsed) < MIN_PACKING
    assert not m["ok"] and "collapsed" in m["why"], m


def test_packing_admits_a_micelle_and_still_rejects_a_collapse():
    """A micelle packs TIGHTER than a bilayer by geometry, and the gate must survive that.

    Calibrated against both structures because a threshold fitted to one shape silently rejects the
    other: at 0.70, tuned on a bilayer, a geometrically perfect planted micelle was called a
    collapse. Micelle lipids converge radially, so inner tail beads sit closer than contact by
    construction -- the packing parameter appearing as a floor on the metric.
    """
    from bicelle2d import build
    from harness import MIN_PACKING, packing
    from references import micelle_2d, relax, spanning_bilayer_2d

    kw = dict(kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0,
              bond_span=2.0, n_water=250, polarity=0.80, head_q=1.2, hydrophobic=0.6)

    bil = spanning_bilayer_2d(build, **kw)
    assert packing(bil) > 0.95, "a bilayer planted at contact must read ~1.0; lower means the "\
                                "metric is counting solvent as a neighbour again"
    mic = micelle_2d(build, n_lip=20, **kw)
    assert packing(mic) < packing(bil), "a micelle packs tighter than a bilayer by geometry"
    assert packing(relax(mic, 500)) > MIN_PACKING, "the gate must ADMIT a real micelle"

    collapsed = spanning_bilayer_2d(build, **kw)
    collapsed.X[:, :collapsed.pd] *= 0.15
    assert packing(collapsed) < MIN_PACKING, "and must still reject a genuine collapse"
