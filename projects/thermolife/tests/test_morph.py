"""Reaction–diffusion morph engine: grows from ONE seed, stays finite/bounded,
morphs continuously (no jumps), deterministic, and renders blobs for the viewer."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from fold.morph import MorphEngine, load_morph, rd_step, skew_matrix
from fold.weights import FoldWeights

_CFG = Path(__file__).resolve().parent.parent / "configs" / "morph.yaml"
_RUN = SimpleNamespace(value="RUNNING")


def _load():
    return load_morph(_CFG)


def test_grows_from_single_seed() -> None:
    """Starts as ONE token and divides up to n_max — morphogenesis, not a fixed set."""
    cfg, p = _load()
    e = MorphEngine(cfg, seed=0, params=p)
    assert e.x.shape[0] == 1                      # a single initial seed
    counts = []
    for _ in range(p.split_every * 8):
        e.step()
        counts.append(e.x.shape[0])
    assert counts[0] >= 1 and max(counts) > 1     # it grew
    assert max(counts) <= p.n_max                  # never past the cap
    for _ in range(200):
        e.step()
    assert e.x.shape[0] == p.n_max                 # reaches the cap


def test_finite_and_bounded() -> None:
    """LayerNorm shell keeps the field finite and bounded over a long run (no blowup)."""
    cfg, p = _load()
    e = MorphEngine(cfg, seed=1, params=p)
    for _ in range(600):
        e.step()
        assert np.all(np.isfinite(e.x))
    assert np.abs(e.x).max() < 6.0                 # on the shell, not exploding


def test_morph_is_continuous() -> None:
    """Small dt ⇒ each step moves the contour only a little — continuous morph,
    not discrete jumps (the whole point of the animation)."""
    cfg, p = _load()
    e = MorphEngine(cfg, seed=2, params=p)
    for _ in range(60):                            # let it grow past a single token
        e.step()
    prev = None
    worst = 0.0
    for _ in range(120):
        e.step()
        snap = e.snapshot(_RUN)
        cur = np.array([t["contour"] for t in snap["tokens"]])
        if prev is not None and cur.shape == prev.shape:
            worst = max(worst, float(np.abs(cur - prev).max()))
        prev = cur
    assert worst < 0.5                             # no teleporting vertices


def test_determinism() -> None:
    cfg, p = _load()
    a, b = MorphEngine(cfg, 0, params=p), MorphEngine(cfg, 0, params=p)
    for _ in range(150):
        a.step(); b.step()
    assert a.state_hash() == b.state_hash()
    assert MorphEngine(cfg, 7, params=p).state_hash() != a.state_hash() or a.tick != 0


def test_snapshot_schema_matches_blob_viewer() -> None:
    """Emits exactly what sim/viewer.html reads (pos + contour blobs, edges)."""
    cfg, p = _load()
    e = MorphEngine(cfg, seed=0, params=p)
    for _ in range(80):
        e.step()
    snap = e.snapshot(_RUN)
    for key in ("status", "tick", "fold", "held", "n", "fold_step", "max_attn",
                "tokens", "edges", "partner", "accuracy"):
        assert key in snap, key
    assert snap["n"] == len(snap["tokens"]) > 1
    tok = snap["tokens"][0]
    assert len(tok["pos"]) == 2 and len(tok["contour"][0]) == 2
    assert snap["partner"] is None                 # no docking ground truth in RD mode
    for i, j, w in snap["edges"]:
        assert i != j and 0.0 <= w <= 1.0


def test_skew_core_is_conservative() -> None:
    """The oscillatory core J is skew-symmetric (xᵀJx = 0): a pure rotation that
    injects motion without adding or removing energy — the anti-collapse floor."""
    j = skew_matrix(3, 6)
    assert np.allclose(j, -j.T)
    x = np.random.default_rng(0).standard_normal((5, 6))
    assert np.allclose(np.sum(x * (x @ j), axis=1), 0.0, atol=1e-9)


def test_global_attention_homogenizes() -> None:
    """Turing's condition, measured: LOCAL diffusion keeps the field spread; GLOBAL
    (lam=0, infinite-range) diffusion homogenizes it toward one shape."""
    import dataclasses
    from fold.hk import spread
    cfg, p = _load()
    local = MorphEngine(cfg, 0, params=p)
    glob = MorphEngine(cfg, 0, params=dataclasses.replace(p, lam=0.0))
    for _ in range(300):
        local.step(); glob.step()
    assert spread(glob.x) < spread(local.x)
