"""Enforce the strict transformer-only HARD_REQUIREMENT on the pure + packing engines.

Every dynamical operation must be attention / MLP / LayerNorm / structured-linear. This greps
the step paths for forbidden force-like / ledger / variable-N patterns. (Coarse but catches the
regressions we care about: a raw 1/d² kernel, an energy book, token insert/delete.)
"""

from __future__ import annotations

import inspect
import re

import block  # noqa: F401
import engine  # noqa: F401 (legacy force engine is intentionally NOT checked)
import pack
import pure

# forbidden in the transformer-only dynamics: divergent radial force kernels, energy ledgers,
# variable token count.
_FORBIDDEN = [
    r"/\s*\(?\s*d2\s*\*\s*np\.sqrt",   # 1/d³ ⇒ 1/d² radial force
    r"/\s*d\b",                          # raw 1/d
    r"1\s*/\s*d2",                       # 1/d²
    r"\benergy\b|\bledger\b|\bmetabol",  # energy bookkeeping
    r"np\.(append|delete|concatenate)\([^)]*axis\s*=\s*0",  # add/remove tokens (variable N)
]


def _step_source(mod) -> str:
    src = []
    for _, obj in inspect.getmembers(mod, inspect.isclass):
        if hasattr(obj, "step"):
            src.append(inspect.getsource(obj.step))
    return "\n".join(src)


def test_pure_is_transformer_only() -> None:
    s = _step_source(pure)
    for pat in _FORBIDDEN:
        assert not re.search(pat, s), f"pure.step contains forbidden pattern: {pat}"


def test_pack_is_transformer_only() -> None:
    s = _step_source(pack)
    for pat in _FORBIDDEN:
        assert not re.search(pat, s), f"pack.step contains forbidden pattern: {pat}"


def test_pack_repel_is_bounded_attention() -> None:
    # the repel must be a row-stochastic attention (softmax), not a divergent kernel.
    s = _step_source(pack)
    assert "A_repel" in s and "exp(" in s, "repel must be a softmax attention head"
