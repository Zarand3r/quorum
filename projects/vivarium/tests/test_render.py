"""Step 1 (M0) — read-only render (P5) + grounded render (P8).

P5: snapshotting must never perturb the dynamics.
P8: the drawn contour is *the same* `X·W_c` the attention query uses — not a
decorative overlay. Because `W_c` selects the shape channels, the blob literally
*is* the query.
"""

from __future__ import annotations

import numpy as np

from block import attention_matrix, contour_coeffs, make_weights, morph_state
from config import DEFAULTS, VivariumConfig
from engine import Engine
from render import snapshot, token_contours
from substrate import init_state


def _cfg(**over) -> VivariumConfig:
    return VivariumConfig(**{**DEFAULTS, **over})


def test_snapshot_is_read_only() -> None:
    # An engine that snapshots between steps must match one that never snapshots.
    cfg = _cfg()
    a, b = Engine(cfg, seed=0), Engine(cfg, seed=0)
    for _ in range(20):
        _ = a.snapshot()
        a.step()
        b.step()
    assert a.X.tobytes() == b.X.tobytes(), "snapshot() perturbed the dynamics"


def test_snapshot_schema() -> None:
    cfg = _cfg()
    snap = Engine(cfg, seed=0).snapshot()
    assert snap["n"] == cfg.N
    assert len(snap["tokens"]) == cfg.N
    tok = snap["tokens"][0]
    assert {"x", "y", "c"} <= tok.keys()
    assert len(tok["c"]) == cfg.shape_dim  # 2K contour coefficients


def test_render_uses_the_blocks_own_Wc() -> None:
    cfg = _cfg()
    X = init_state(cfg, seed=0)
    w = make_weights(cfg, seed=0)
    assert np.array_equal(token_contours(X, w), contour_coeffs(morph_state(X), w.W_c)), (
        "the renderer must read z·W_c with the block's own W_c (identity, not correlation)"
    )


def test_perturbing_shape_moves_blob_and_attention() -> None:
    cfg = _cfg()
    X = init_state(cfg, seed=0)
    w = make_weights(cfg, seed=0)
    C0 = token_contours(X, w)
    A0 = attention_matrix(X, w, cfg)

    # perturb agent i's shape channels.
    i = 3
    Xp = X.copy()
    sl = slice(cfg.pos_dim, cfg.pos_dim + cfg.shape_dim)
    Xp[i, sl] += 0.5

    Cp = token_contours(Xp, w)
    Ap = attention_matrix(Xp, w, cfg)
    assert not np.allclose(Cp[i], C0[i]), "blob must move when the shape channels move"
    assert not np.allclose(Ap[i], A0[i]), "attention row must move when the query moves"
