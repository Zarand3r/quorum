"""The vesicle gate must SEPARATE its panel, and each clause must be able to fail on its own."""
from __future__ import annotations

import numpy as np

import _mixture
import vesicle_gate
from field import HEAD


def _planted(plant, N=56, L=100.0):
    nw = int(round(0.55 * L ** 2 / np.pi * 4)) - N * 5
    X, sp, b, mols, _, _ = _mixture.build(0, N, nw, L, 2, plant=plant, branched=True, seed=1)
    mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
    return np.ascontiguousarray(X, dtype=np.float64), sp, mm, L


def test_panel_separates():
    """The whole point: every positive scores above every negative."""
    assert vesicle_gate.validate() == 0


def test_closure_clause_rejects_a_nearly_closed_arc():
    """arc0.75 is the hardest negative — open, but most of the way round."""
    ok, score, d = vesicle_gate.vesicle(*_planted("arc0.75"))
    assert not ok and d["closure"] == 0.0


def test_bilayer_clause_can_fail_on_a_monolayer():
    """Delete one leaflet from a planted ring: still closed-ish, no longer two leaflets.

    Without this the bilayer clause could return ~0.5 for everything and nothing would notice — the
    failure mode that produced three unusable metrics on 2026-09-14.
    """
    X, sp, mols, L = _planted("arc1.0")
    heads = X[[m[0] for m in mols]]
    r = np.linalg.norm(heads - heads.mean(axis=0), axis=1)
    outer = np.where(r > np.median(r))[0]          # keep ONE leaflet only
    frac = vesicle_gate.inward_fraction(X, sp, mols, L, outer)
    full = vesicle_gate.inward_fraction(X, sp, mols, L, np.arange(len(mols)))
    assert abs(full - 0.5) < 0.25, f"a real bilayer must sit near 0.5, got {full}"
    assert abs(frac - 0.5) > abs(full - 0.5), (
        f"one leaflet ({frac}) must be further from 0.5 than two ({full}) — "
        "otherwise the clause cannot distinguish a monolayer")


def test_the_three_micelle_state_is_rejected():
    """The state that scored 0.5997 against a 0.45 threshold on the previous curl metric."""
    import pathlib
    p = pathlib.Path(__file__).parent.parent / "docs/states_curl/CURL_s2.0_nr0.3335_sd801.npz"
    if not p.exists():
        return
    z = np.load(p)
    ok, score, _ = vesicle_gate.vesicle(z["X"], z["species"], z["mols"], float(z["L"]))
    assert not ok and score == 0.0
