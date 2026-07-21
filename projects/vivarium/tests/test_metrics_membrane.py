"""Validate the membrane metric on HAND-BUILT fixtures — it must match what the eye sees:
a bilayer scores high-H + high-sheetness; a micelle high-H + low-sheetness; disorder low-H.
Only once the metric provably matches these do we trust it to tune self-assembly.
"""

from __future__ import annotations

import numpy as np

from metrics_membrane import LIPID, WATER, measure, membrane_order

_L = 14.0


def _bilayer():
    """Two rows of lipids, tails pointing at each other (inward), heads out; water above/below."""
    xs = np.linspace(-3, 3, 12)
    top = np.stack([xs, np.full_like(xs, 0.4)], 1)     # top row, tail points DOWN (+o = -y)
    bot = np.stack([xs, np.full_like(xs, -0.4)], 1)    # bottom row, tail points UP (+o = +y)
    pos = np.concatenate([top, bot])
    orient = np.concatenate([np.tile([0.0, -1.0], (12, 1)), np.tile([0.0, 1.0], (12, 1))])
    species = np.full(24, LIPID)
    # water slabs above and below
    wx = np.linspace(-3, 3, 10)
    w = np.concatenate([np.stack([wx, np.full_like(wx, 1.6)], 1),
                        np.stack([wx, np.full_like(wx, -1.6)], 1)])
    pos = np.concatenate([pos, w]); orient = np.concatenate([orient, np.zeros_like(w)])
    species = np.concatenate([species, np.full(len(w), WATER)])
    return pos, species, orient


def _micelle():
    """A filled disk of lipids, tails toward the centre; water around."""
    rng = np.random.default_rng(0)
    pts = []
    while len(pts) < 18:
        q = rng.uniform(-1.0, 1.0, 2)
        if q @ q <= 1.0:
            pts.append(q)
    p = np.array(pts) * 0.9
    orient = -p / (np.linalg.norm(p, axis=1, keepdims=True) + 1e-9)   # tail toward centre
    species = np.full(len(p), LIPID)
    wr = 2.2; ang = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    w = np.stack([wr * np.cos(ang), wr * np.sin(ang)], 1)
    pos = np.concatenate([p, w]); orient = np.concatenate([orient, np.zeros_like(w)])
    species = np.concatenate([species, np.full(len(w), WATER)])
    return pos, species, orient


def _disordered():
    rng = np.random.default_rng(1)
    pos = rng.uniform(-3, 3, (40, 2))
    orient = rng.standard_normal((40, 2)); orient /= np.linalg.norm(orient, axis=1, keepdims=True)
    species = np.array([LIPID if i % 2 else WATER for i in range(40)])
    return pos, species, orient


def test_bilayer_scores_membrane() -> None:
    m = measure(*_bilayer(), _L)
    assert m["H"] > 0.7, f"bilayer tails must be buried, H={m['H']}"
    assert m["sheetness"] > 2.5, f"bilayer must read as a ribbon, sheetness={m['sheetness']}"


def test_micelle_high_H_low_sheet() -> None:
    m = measure(*_micelle(), _L)
    assert m["H"] > 0.6, f"micelle tails buried, H={m['H']}"
    assert m["sheetness"] < 2.2, f"micelle must read round, not a ribbon, sheetness={m['sheetness']}"


def test_disordered_low_H() -> None:
    m = measure(*_disordered(), _L)
    assert m["H"] < 0.6, f"disordered mixture must not read as assembled, H={m['H']}"


def test_bilayer_beats_disordered_and_is_a_sheet() -> None:
    # the discriminating claim: bilayer > micelle > disordered on sheetness; bilayer,micelle >> disordered on H.
    b, mi, d = measure(*_bilayer(), _L), measure(*_micelle(), _L), measure(*_disordered(), _L)
    assert b["H"] > d["H"] and mi["H"] > d["H"]
    assert b["sheetness"] > mi["sheetness"], "a bilayer ribbon must be more elongated than a micelle"


def test_order_parameter_matches_eye() -> None:
    # director order S (unsigned): a bilayer's two antiparallel leaflets still share ONE axis → S→1;
    # side (bond ⊥ normal): a bilayer's neighbours are beside within a leaflet → side high. Disorder → both low.
    Sb, sideb = membrane_order(*_bilayer(), _L)
    Sd, _ = membrane_order(*_disordered(), _L)
    assert Sb > 0.85, f"bilayer leaflets share one director, S={Sb}"
    # in-leaflet neighbours are beside (side→1), cross-leaflet ones are stacked (side→0); the mix sits ~0.6
    assert sideb > 0.6, f"bilayer neighbours mostly side-by-side, side={sideb}"
    assert Sb > Sd, f"ordered membrane must out-score disorder on director order ({Sb} vs {Sd})"
