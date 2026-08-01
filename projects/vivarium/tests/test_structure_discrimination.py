"""Plant EVERY candidate structure and require the metrics to tell them apart.

"Plant a bilayer, check it reads success" is necessary but nowhere near sufficient: a metric that
returns success for everything passes it. That is not hypothetical here -- `lamellar` reads 1.000 on a
collapsed droplet, which is how several false claims survived.

So this builds each structure by hand and asserts the DISCRIMINATION, not the value:

    structure   lamellar   aspect        hollow        distinguishing feature
    bilayer     high       LOW (thin)    -             flat: two long axes, one short
    micelle     high       HIGH (round)  HIGH (filled) tails fill the core
    vesicle     high       HIGH (round)  LOW (empty)   sealed shell, empty middle
    random      null       -             -             no order at all

Bilayer vs micelle is separated by `aspect`. Micelle vs vesicle is separated ONLY by `hollow` -- both
are round with heads out, so any search ranking on `aspect` alone would discard a vesicle as a
droplet, which is precisely the structure we are hunting.
"""

import numpy as np
import pytest

from config import DEFAULTS, VivariumConfig
from harness import measure
from polar_pack import PolarPackEngine


def _engine(n_lip, n_tail=2, bound=12.0):
    nb = 1 + n_tail
    cfg = VivariumConfig(**{**DEFAULTS, "N": nb * n_lip, "pos_dim": 3, "n_harmonics": 2,
                            "pos_bound": bound})
    e = PolarPackEngine(cfg, 0, water_frac=0.0, chain_frac=1.0, polarity=0.0, repel=12.0,
                        n_tail=n_tail, rad_head=0.0, head_q=0.0, bond_span=2.0, aniso=0.0)
    e.wall_axes = ()
    e.vel[:] = 0.0
    return e


def _bilayer(n_lip=288):
    # A SPANNING bilayer must tile x-y at ~1.0 lipid spacing, so the box follows from the
    # lipid count: k = ceil(sqrt(per)) columns at unit spacing means half-width k/2. Too
    # large a box and the lipids never touch ('no aggregate'); too small and they overlap.
    # TWO constraints, both discovered by this test failing:
    #   lateral: k columns at ~1.0 spacing means half-width k/2, or the lipids never touch
    #   normal:  half-width must EXCEED the membrane thickness, otherwise minimum image folds the two
    #            leaflets onto each other and a flat bilayer measures as round (aspect 0.98)
    per = n_lip // 2
    k = int(np.ceil(np.sqrt(per)))
    e = _engine(n_lip, bound=k / 2.0)
    mol, nb = e._mol, e._mol.shape[1]
    per, B = len(mol) // 2, e.cfg.pos_bound
    k = int(np.ceil(np.sqrt(per)))
    xs = (np.arange(k) + 0.5) / k * 2 * B - B
    gx, gy = np.meshgrid(xs, xs, indexing="ij")
    flat = np.stack([gx.ravel(), gy.ravel()], axis=1)
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        for bead in range(nb):
            off = 0.5 + (nb - 1 - bead) * 1.0
            e.X[idx[:, bead], 0] = flat[:len(idx), 0]
            e.X[idx[:, bead], 1] = flat[:len(idx), 1]
            e.X[idx[:, bead], 2] = sgn * off
    return e


def _sphere_dirs(n, seed=1):
    rng = np.random.default_rng(seed)
    u = rng.standard_normal((n, 3))
    return u / np.linalg.norm(u, axis=1, keepdims=True)


def _micelle(n_lip=60):
    # a compact ball; any roomy box works
    """Heads on the surface, tails to the centre. FILLED."""
    e = _engine(n_lip, bound=7.0)
    mol, nb = e._mol, e._mol.shape[1]
    u = _sphere_dirs(len(mol))
    for bead in range(nb):
        e.X[mol[:, bead], :3] = u * (0.6 + (nb - 1 - bead) * 1.0)
    return e


def _vesicle(n_lip=180, R=4.0):
    """Closed shell: outer leaflet heads out, inner leaflet heads in. EMPTY middle.

    R and the box are chosen so the OUTER radius (R + molecule length) leaves clear margin inside the
    periodic box. At R=5 in a box of 16 the shell reached 7.5 and wrapped, and the wrapped copy made a
    sphere read as flat (aspect 0.39) and a hollow shell read as filled (hollow 3.6). A reference
    structure that does not fit its own container invalidates every metric calibrated on it -- the
    same defect the planted bilayer had.
    """
    # Unwrapping relative to a SINGLE reference bead requires the structure's DIAMETER to be under
    # L/2, or the far side wraps onto the near side: at diameter 13 in a box of 20 the shell folded
    # into itself and read as filled (hollow 2.6) and flat (aspect 0.39).
    e = _engine(n_lip, bound=16.0)
    mol, nb = e._mol, e._mol.shape[1]
    n = len(mol)
    u = _sphere_dirs(n)
    half = n // 2
    for m in range(n):
        outer = m < half
        for bead in range(nb):
            depth = 0.5 + (nb - 1 - bead) * 1.0        # head outermost within its own leaflet
            r = R + depth if outer else R - depth
            e.X[mol[m, bead], :3] = u[m] * r
    return e


def _random(n_lip=128):
    e = _engine(n_lip, bound=6.0)
    mol = e._mol
    rng = np.random.default_rng(0)
    B = e.cfg.pos_bound
    cen = rng.uniform(-B, B, (len(mol), 3))
    ax = _sphere_dirs(len(mol), seed=2)
    for b in range(mol.shape[1]):
        e.X[mol[:, b], :3] = cen + (1.0 - b) * ax
    return e


def test_planted_references_fit_their_box():
    """A reference must not wrap, or every metric calibrated on it is invalid.

    A SPANNING bilayer is periodic in x-y BY DESIGN, so only its normal (z) has to fit; a finite
    micelle or vesicle must fit in every direction. Getting this wrong is what made a planted sphere
    read as flat (aspect 0.39) and a hollow shell read as filled (hollow 3.6).
    """
    for name, fn, axes in (("bilayer", _bilayer, (2,)),
                           ("micelle", _micelle, (0, 1, 2)),
                           ("vesicle", _vesicle, (0, 1, 2))):
        e = fn()
        P = e.X[e._mol.ravel(), :3]
        B = e.cfg.pos_bound
        for ax in axes:
            span = float(np.abs(P[:, ax]).max())
            assert span < B - 1.0, (f"{name} reaches {span:.1f} on axis {ax} in a box of half-width "
                                    f"{B:.1f}: it wraps, so every metric on it is invalid")


@pytest.fixture(scope="module")
def scores():
    return {name: measure(fn()) for name, fn in
            (("bilayer", _bilayer), ("micelle", _micelle),
             ("vesicle", _vesicle), ("random", _random))}


def test_every_planted_structure_is_admissible(scores):
    """A hand-built structure must not be refused; if it is, the gates are wrong, not the structure."""
    for name in ("bilayer", "micelle", "vesicle"):
        assert scores[name]["ok"], f"{name} was disqualified: {scores[name]['why']}"


def test_aspect_separates_bilayer_from_round_structures(scores):
    """A bilayer is thin in one axis; a micelle and a vesicle are round. This is the ONLY thing that
    distinguishes a membrane from a blob, so it must have real margin."""
    assert scores["bilayer"]["aspect"] < 0.45
    assert scores["micelle"]["aspect"] > 0.60
    assert scores["vesicle"]["aspect"] > 0.60
    assert scores["micelle"]["aspect"] - scores["bilayer"]["aspect"] > 0.25


def test_hollow_separates_vesicle_from_micelle(scores):
    """A micelle and a vesicle are BOTH round with heads out, so aspect and lamellar cannot tell them
    apart. Only emptiness at the centre can, and a search ranking on aspect alone would therefore
    discard a vesicle as a droplet."""
    assert scores["vesicle"]["hollow"] < scores["micelle"]["hollow"], (
        f"vesicle hollow={scores['vesicle']['hollow']:.2f} is not below "
        f"micelle hollow={scores['micelle']['hollow']:.2f}")
    assert scores["vesicle"]["hollow"] < 0.5, "a sealed vesicle must read as EMPTY at the core"


def test_align_separates_lamellar_from_radial(scores):
    """`align` is the nematic order of the lipid axes and is THE lamellar discriminator.

    A bilayer puts every axis along +/-n so align -> 1; a micelle or vesicle points them radially so
    align -> 0. Measured: bilayer 1.000, micelle 0.086, vesicle 0.033, random 0.084.
    """
    assert scores["bilayer"]["align"] > 0.90
    assert scores["micelle"]["align"] < 0.30
    assert scores["vesicle"]["align"] < 0.30
    assert scores["random"]["align"] < 0.30


def test_lamellar_ANTI_discriminates_and_must_not_be_used_alone(scores):
    """Pins the trap that cost this project six retractions.

    `lamellar` asks whether a head sits farther out than its own tails, which is true of ANY heads-out
    structure. Measured, it scores a MICELLE (0.967) ABOVE a BILAYER (0.889): it does not merely fail
    to discriminate, it points the wrong way. Every "lamellar ~0.9, partial order" reading in this
    project's history was consistent with a micelle.
    """
    assert scores["micelle"]["lamellar"] > 0.85, "the trap is real: a micelle scores high on lamellar"


def test_random_is_at_the_null(scores):
    """Without a measured null the scale has no zero."""
    assert scores["random"]["lamellar"] < 0.75
