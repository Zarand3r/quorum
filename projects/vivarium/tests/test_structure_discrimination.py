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

import math

import numpy as np
import pytest

from config import DEFAULTS, VivariumConfig
from harness import BOND_REST, largest_cluster, measure
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


def _sphere_dirs(n):
    """n directions spread EVENLY over the sphere (Fibonacci spiral), not sampled at random.

    Normalised Gaussians are Poisson-random on the sphere, and Poisson points clump: their median
    nearest-neighbour distance is 2r*sqrt(ln2/n), against 2r*sqrt(pi/n) for an even arrangement --
    a factor of 2.1 closer. On the planted vesicle that put the shells at 0.59 of contact no matter
    how the radii or the leaflet split were chosen, because the clumping is in the sampling itself.

    Points are returned ordered along the spiral, so a CONTIGUOUS slice is a band rather than a
    subsample of the whole sphere. Callers that need two independent shells must build each with its
    own call.
    """
    k = np.arange(n) + 0.5
    z = 1.0 - 2.0 * k / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    th = np.pi * (1.0 + 5.0 ** 0.5) * k
    return np.stack([r * np.cos(th), r * np.sin(th), z], axis=1)


def _random_dirs(n, seed=1):
    """Poisson-random directions. ONLY for the null reference, which has to be genuinely disordered.

    Every ordered structure wants `_sphere_dirs` instead: random directions clump, and that clumping
    is what put the planted shells at 0.59 of contact. Here the clumping is the point.
    """
    rng = np.random.default_rng(seed)
    u = rng.standard_normal((n, 3))
    return u / np.linalg.norm(u, axis=1, keepdims=True)


def _micelle(n_lip=60):
    """A round FILLED aggregate: radially-oriented molecules packed through the whole ball.

    This is the contrast partner for `_vesicle` -- round and filled against round and hollow -- and
    that contrast is the only thing `hollow` and `enclosed` are asked to make.

    It is deliberately NOT the concentric-shells geometry it used to be. That version put every
    lipid's tail END on one inner shell of radius 0.6, i.e. 0.32 of contact, and a shell of n points
    at radius r only holds them ~2r*sqrt(pi/n) apart. Nothing in the harness could reject it until
    `packing` existed, so both discriminators were calibrated against an impossible structure.

    Shells cannot be repaired here, because THIS LIPID CANNOT FORM A MICELLE AT ALL. With two tail
    beads the packing parameter is

        P = v / (a0 * l) = 1.05 / (1.0 * 2.0) = 0.52

    which is the bilayer range (1/2 to 1); micelles need P < 1/3. Enlarging the inner shell until it
    is sterically legal empties the core and turns the reference into a small vesicle, which is
    exactly what happened -- `hollow` then read 0.00 for both. A true micelle reference would need a
    different molecule (one tail, or a wider head), and that is a separate structure, not a fix here.

    Molecules stay RADIALLY oriented and their centres are staggered through the volume, with radii
    as ((m+0.5)/n)^(1/3) so density is uniform rather than piled on a surface. Radial orientation is
    not cosmetic: it is what makes this a droplet rather than a slab, and it is what `align` and
    `lamellar` are calibrated against. A space-filling cubic lattice packs perfectly but leaves every
    molecule parallel, which reads as high nematic order and destroys exactly that contrast.

    The fill fraction is deliberately loose. A tight ball placed by construction rather than by
    relaxation measured 0.59 of contact, because sprinkling points at uniform density does not
    respect exclusion the way a relaxed liquid does; a looser ball is still unambiguously FILLED
    against a vesicle's empty lumen, which is the only contrast this reference has to carry.
    With directions spread evenly rather than sampled at random the ball packs far better, so the
    fill can stay compact enough for the droplet to fit its own box.
    """
    # The box follows from R, not the other way round: the droplet's DIAMETER must stay under L/2 or
    # it wraps onto itself, and a loose fill in the old bound=7.0 box did exactly that -- `hollow`
    # went NaN and separate aggregates merged. Same defect the vesicle and bilayer each had once.
    R = ((n_lip * (1 + 2) * (math.pi / 6.0) * BOND_REST ** 3)
         / (0.35 * (4.0 / 3.0) * math.pi)) ** (1.0 / 3.0)
    e = _engine(n_lip, bound=max(7.0, 1.4 * 2.0 * (R + BOND_REST)))
    mol, nb = e._mol, e._mol.shape[1]
    n = len(mol)
    u = _sphere_dirs(n)
    r_mid = R * ((np.arange(n) + 0.5) / n) ** (1.0 / 3.0)
    for bead in range(nb):
        # head (bead 0) sits radially OUTWARD of its own tails, so heads still face out
        off = (nb - 1) / 2.0 - bead
        e.X[mol[:, bead], :3] = u * (r_mid + off * BOND_REST)[:, None]
    return e


def _vesicle(n_lip=260, R=4.0):
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
    # The leaflets are split by AREA, not in half. A vesicle's inner leaflet wraps a much smaller
    # sphere, so an even split crams it: 90 molecules on the r=1.5 inner shell sit 0.63 of contact
    # apart, and until `packing` existed nothing could say so. Real vesicles carry the same
    # constraint, which is why their leaflets hold different lipid counts.
    #   n_inner / n_outer = (r_inner / r_outer)^2
    # n_lip then follows from wanting the OUTER shell dense enough to stay one cluster: spacing goes
    # as 2*r*sqrt(pi/n), and at n_lip=180 the outer shell sits 1.76 apart, past the 1.6 contact
    # cutoff, so a legal vesicle would have measured as fragmented instead.
    e = _engine(n_lip, bound=16.0)
    mol, nb = e._mol, e._mol.shape[1]
    n = len(mol)
    depth_max = 0.5 + (nb - 1) * 1.0
    r_i, r_o = R - depth_max, R + depth_max
    n_out = int(round(n / (1.0 + (r_i / r_o) ** 2)))
    # each leaflet gets its OWN spiral: a contiguous slice of one spiral is a band, which would
    # leave the inner leaflet as a cap over one pole rather than a closed shell.
    u = np.concatenate([_sphere_dirs(n_out), _sphere_dirs(n - n_out)])
    for m in range(n):
        outer = m < n_out
        for bead in range(nb):
            depth = 0.5 + (nb - 1 - bead) * 1.0        # head outermost within its own leaflet
            r = R + depth if outer else R - depth
            e.X[mol[m, bead], :3] = u[m] * r
    return e


def _bicelle(n_lip=500, R=9.0, n_water=600):
    """A FINITE bilayer disc: two leaflets, shared normal, and a RIM of exposed tails.

    This is the structure the project is actually hunting, and until now it was absent from the suite:
    every metric was validated against bilayer / micelle / vesicle / random, none of which has a rim.
    A bicelle differs from a SPANNING bilayer only in being finite, so `edge` -- the rim metric -- is
    the thing that separates them, and it had never been checked against a known answer.
    """
    # R must be much larger than the membrane thickness or the disc is a squat cylinder, not a
    # bicelle: at R=5 with thickness 5 the aspect ratio is 0.46, barely flatter than a sphere. A real
    # bicelle has radius several times its thickness. Box half-width clears R + molecule length.
    # EXPLICIT WATER IS REQUIRED. `edge` is defined by tail-water contact, so a rim cannot be
    # measured without solvent: it returns NaN. A bicelle is therefore unverifiable in ANY
    # solvent-free run, whatever else is computed -- which is a hard constraint on the experiments,
    # not just the tests.
    nb_ = 3
    tot = nb_ * n_lip + n_water
    cfg = VivariumConfig(**{**DEFAULTS, "N": tot, "pos_dim": 3, "n_harmonics": 2,
                            "pos_bound": 14.0})
    e = PolarPackEngine(cfg, 0, water_frac=n_water / tot, chain_frac=nb_ * n_lip / tot,
                        polarity=0.0, repel=12.0, n_tail=2, rad_head=0.0, head_q=0.0,
                        bond_span=2.0, aniso=0.0)
    e.wall_axes = ()
    e.vel[:] = 0.0
    mol, nb = e._mol, e._mol.shape[1]
    per = len(mol) // 2
    # a disc of radius R: place molecules on a spiral so the density is roughly uniform
    k = np.arange(per)
    rr = R * np.sqrt((k + 0.5) / per)
    th = k * np.pi * (3.0 - np.sqrt(5.0))
    pts = np.stack([rr * np.cos(th), rr * np.sin(th)], axis=1)
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        for bead in range(nb):
            off = 0.5 + (nb - 1 - bead) * 1.0
            e.X[idx[:, bead], 0] = pts[:len(idx), 0]
            e.X[idx[:, bead], 1] = pts[:len(idx), 1]
            e.X[idx[:, bead], 2] = sgn * off
    # solvent everywhere outside the disc, so the rim has water to touch
    rng = np.random.default_rng(7)
    wi = e._wi
    B = e.cfg.pos_bound
    pos = rng.uniform(-B, B, (len(wi), 3))
    inside = (np.hypot(pos[:, 0], pos[:, 1]) < R - 0.5) & (np.abs(pos[:, 2]) < 2.6)
    pos[inside, 2] = np.sign(pos[inside, 2] + 1e-9) * rng.uniform(3.0, B, inside.sum())
    e.X[wi, :3] = pos
    return e


def _spanning_bilayer_with_water(n_lip=288, n_water=400):
    """A spanning bilayer PLUS solvent, so `edge` has water to detect. A periodic sheet has NO rim,
    so a correct `edge` must read near zero here -- that is the negative control it never had."""
    per = n_lip // 2
    k = int(np.ceil(np.sqrt(per)))
    nb = 3
    cfg = VivariumConfig(**{**DEFAULTS, "N": nb * n_lip + n_water, "pos_dim": 3,
                            "n_harmonics": 2, "pos_bound": k / 2.0})
    e = PolarPackEngine(cfg, 0, water_frac=n_water / (nb * n_lip + n_water),
                        chain_frac=nb * n_lip / (nb * n_lip + n_water),
                        polarity=0.0, repel=12.0, n_tail=2, rad_head=0.0, head_q=0.0,
                        bond_span=2.0, aniso=0.0)
    e.wall_axes = ()
    e.vel[:] = 0.0
    mol, B = e._mol, e.cfg.pos_bound
    per = len(mol) // 2
    xs = (np.arange(k) + 0.5) / k * 2 * B - B
    gx, gy = np.meshgrid(xs, xs, indexing="ij")
    flat = np.stack([gx.ravel(), gy.ravel()], axis=1)
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        for bead in range(mol.shape[1]):
            off = 0.5 + (mol.shape[1] - 1 - bead) * 1.0
            e.X[idx[:, bead], 0] = flat[:len(idx), 0]
            e.X[idx[:, bead], 1] = flat[:len(idx), 1]
            e.X[idx[:, bead], 2] = sgn * off
    # water only OUTSIDE the membrane, as it would be physically
    rng = np.random.default_rng(4)
    wi = e._wi
    zz = rng.uniform(2.6, B, len(wi)) * rng.choice([-1.0, 1.0], len(wi))
    e.X[wi, 0] = rng.uniform(-B, B, len(wi))
    e.X[wi, 1] = rng.uniform(-B, B, len(wi))
    e.X[wi, 2] = zz
    return e


def _solvated_sphere(n_lip, R, hollow_shell, n_water=1800, bound=12.0):
    """A sphere WITH solvent, so `enclosed` can be measured.

    R, the box and the water count are chosen so the LUMEN holds a countable number of waters. At
    R=5 in a box of 32 with 900 waters the expected count inside is ~1.6, so a Poisson zero is likely
    and the test reads 0.000 for a perfectly good vesicle -- an underpowered test, not a bad metric.

    hollow_shell=True gives a sealed vesicle: two leaflets forming a shell of radius R, with water
    both inside and outside. hollow_shell=False gives a filled micelle: tails to the centre, water
    only outside. The pair is the only way to validate `enclosed`, which is the stage-4 signature and
    the feature that makes a vesicle a vesicle rather than a shell in vacuum.
    """
    nb_ = 3
    tot = nb_ * n_lip + n_water
    cfg = VivariumConfig(**{**DEFAULTS, "N": tot, "pos_dim": 3, "n_harmonics": 2,
                            "pos_bound": bound})
    e = PolarPackEngine(cfg, 0, water_frac=n_water / tot, chain_frac=nb_ * n_lip / tot,
                        polarity=0.0, repel=12.0, n_tail=2, rad_head=0.0, head_q=0.0,
                        bond_span=2.0, aniso=0.0)
    e.wall_axes = ()
    e.vel[:] = 0.0
    mol, nb = e._mol, e._mol.shape[1]
    n = len(mol)
    # separate spirals per leaflet, for the same reason as _vesicle: a contiguous slice of one
    # spiral is a band over one pole, not a closed shell.
    half = n // 2
    # A SHELL needs one spiral per leaflet, since a contiguous slice of one spiral is a band over a
    # pole. A filled BALL needs the opposite: a single spiral of n, because two spirals of n/2 each
    # cover the whole sphere and so hand out directions in near-coincident PAIRS -- which measured
    # 0.39 of contact even after the radii were fixed.
    u = (np.concatenate([_sphere_dirs(half), _sphere_dirs(n - half)]) if hollow_shell
         else _sphere_dirs(n))
    # The FILLED case fills a ball at uniform density. Placing beads at r = depth put every tail end
    # on a shell of radius 0.5, i.e. 0.04 of contact -- the same impossible core `_micelle` had, and
    # for the same reason: a shell of n points at radius r only holds them ~2r*sqrt(pi/n) apart.
    r_fill = ((n * nb * (math.pi / 6.0) * BOND_REST ** 3)
              / (0.35 * (4.0 / 3.0) * math.pi)) ** (1.0 / 3.0)
    r_mid = r_fill * ((np.arange(n) + 0.5) / n) ** (1.0 / 3.0)
    for m in range(n):
        for bead in range(nb):
            depth = 0.5 + (nb - 1 - bead) * 1.0
            if hollow_shell:
                r = (R + depth) if m < half else (R - depth)
            else:
                r = r_mid[m] + ((nb - 1) / 2.0 - bead) * BOND_REST
            e.X[mol[m, bead], :3] = u[m] * r
    rng = np.random.default_rng(11)
    wi = e._wi
    pos = rng.uniform(-bound, bound, (len(wi), 3))
    rr = np.linalg.norm(pos, axis=1)
    if hollow_shell:
        # water is allowed inside the shell and outside it, but not within the leaflets themselves
        bad = (rr > R - 2.6) & (rr < R + 2.6)
        pos[bad] *= ((R + 4.0) / np.maximum(rr[bad], 1e-9))[:, None]
    else:
        # a filled micelle admits no water at all, so clear the whole ball it now occupies
        keep_out = r_fill + 1.5 * BOND_REST
        bad = rr < keep_out
        pos[bad] *= ((keep_out + 1.8) / np.maximum(rr[bad], 1e-9))[:, None]
    e.X[wi, :3] = pos
    return e


def _random(n_lip=128):
    e = _engine(n_lip, bound=6.0)
    mol = e._mol
    rng = np.random.default_rng(0)
    B = e.cfg.pos_bound
    cen = rng.uniform(-B, B, (len(mol), 3))
    ax = _random_dirs(len(mol), seed=2)
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


def test_bicelle_reads_as_a_flat_bilayer_with_a_rim():
    """The structure the project is hunting must be recognisable: lamellar order AND a rim."""
    m = measure(_bicelle())
    assert m["ok"], f"a planted bicelle was disqualified: {m['why']}"
    assert m["align"] > 0.90, f"align={m['align']:.3f}: a bicelle IS a bilayer, axes share a normal"
    assert m["aspect"] < 0.20, f"aspect={m['aspect']:.3f}: a bicelle is a flat disc (R >> thickness)"



def test_edge_separates_a_finite_bicelle_from_a_spanning_bilayer():
    """`edge` is the rim metric and had NEVER been validated.

    It must be read RELATIVE to a control, never against an absolute threshold: `edge` counts lipids
    whose deepest tail bead contacts water, so its value scales with SOLVENT DENSITY. The same planted
    bicelle reads 0.03 in dilute solvent and much more in dense solvent. What is invariant is the
    ORDERING: a finite disc exposes a rim, a periodic sheet has no edges at all.
    """
    bic = measure(_bicelle())
    span = measure(_spanning_bilayer_with_water())
    assert bic["ok"] and span["ok"], f"controls disqualified: {bic['why']} / {span['why']}"
    assert bic["edge"] > span["edge"], (
        f"a finite bicelle (edge={bic['edge']:.3f}) must expose MORE rim than a spanning bilayer "
        f"(edge={span['edge']:.3f}); if not, `edge` cannot verify a bicelle at all")


def test_enclosed_separates_a_sealed_vesicle_from_a_filled_micelle():
    """`enclosed` is the stage-4 signature and had no validation at all.

    A vesicle TRAPS solvent; a micelle fills the same volume with tails and traps none. Neither
    `align` nor `lamellar` can tell these apart (both are round with heads out), and `hollow` only
    says the core is tail-free -- it cannot say the core holds WATER, which is what a vesicle is.
    """
    ves = measure(_solvated_sphere(220, 6.5, True))
    mic = measure(_solvated_sphere(60, 0.0, False))
    assert ves["ok"] and mic["ok"], f"{ves['why']} / {mic['why']}"
    assert ves["enclosed"] > 0.02, f"a sealed vesicle must trap solvent, got {ves['enclosed']:.3f}"
    assert ves["enclosed"] > 3 * max(mic["enclosed"], 1e-3), (
        f"vesicle enclosed={ves['enclosed']:.3f} vs micelle {mic['enclosed']:.3f}: not separated")


def _three_separated_micelles(gap=3.2, n_each=25):
    """Three distinct micelles with clear solvent between them.

    This is the test that was missing, and its absence cost a false VESICLE: with the cutoff at 2.2,
    largest_cluster merged four separate micelles into one "aggregate", and the water BETWEEN them
    read as a lumen (hollow 0.06, enclosed 2.96 -- above bulk density, which is impossible). Only a
    screenshot caught it. Distinct aggregates must stay distinct.
    """
    n_lip = 3 * n_each
    e = _engine(n_lip, bound=14.0)
    mol, nb = e._mol, e._mol.shape[1]
    # gap is set from a MEASURED closest approach, not a calculated one. Lipids point in random
    # directions, so the nearest bead pair between two micelles is not along the centre line: at
    # gap=3.5 the ideal separation is 1.8 but the measured closest approach is 2.39, which the broken
    # 2.2 cutoff does NOT bridge -- so the test passed with the bug reinstated. Three geometries
    # (6.0, 4.0, 3.5) all failed to catch it for this reason. gap=3.2 puts the measured closest approach
    # between the correct cutoff (1.6) and the known-bad one (2.2), so the bug is caught and the
    # fix passes. The window is NARROW: at gap=2.9 both cutoffs merge, because aggregates within
    # ~1.5 units of each other are genuinely ambiguous and no cutoff can separate them. That is an
    # inherent limit of contact-graph clustering, not a defect to tune away.
    centres = np.array([[-gap, 0.0, 0.0], [gap, 0.0, 0.0], [0.0, gap * 1.9, 0.0]])
    # each micelle gets its OWN spiral. Points along one spiral are ordered pole to pole, so slicing
    # a single spiral three ways would give three BANDS rather than three balls, and the closest
    # approach between them would be geometry this test never meant to measure.
    u = np.concatenate([_sphere_dirs(n_each) for _ in range(3)])
    for m in range(len(mol)):
        c = centres[m // n_each]
        for bead in range(nb):
            e.X[mol[m, bead], :3] = c + u[m] * (0.6 + (nb - 1 - bead) * 1.0)
    return e


def test_separate_aggregates_are_not_merged():
    """Three micelles separated by open solvent must NOT be reported as one cluster."""
    e = _three_separated_micelles()
    comp = largest_cluster(e)
    frac = len(comp) / len(e._mol)
    assert frac < 0.5, (
        f"largest_cluster merged distinct aggregates: {len(comp)}/{len(e._mol)} lipids = {frac:.0%} "
        f"in one cluster, when the true answer is ~33%. The water between them then reads as a lumen "
        f"and a cluster of micelles is misclassified as a vesicle.")


def test_cluster_cutoff_has_margin_on_both_sides():
    """The cutoff is bounded from BOTH sides and the window is narrow, so pin it explicitly.

    Too tight and a bilayer's leaflets split (the harness then rejects a real membrane as
    "fragmented"). Too loose and separate aggregates merge (a cluster of micelles reads as a vesicle).
    Both failures happened, hours apart, from the same constant.
    """
    from harness import largest_cluster as lc
    bil = _bilayer()
    assert len(lc(bil)) == len(bil._mol), "cutoff too TIGHT: a bilayer's leaflets were split"
    sep = _three_separated_micelles()
    assert len(lc(sep)) / len(sep._mol) < 0.5, "cutoff too LOOSE: distinct aggregates merged"
