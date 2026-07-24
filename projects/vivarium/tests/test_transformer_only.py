"""Enforce the strict transformer-only HARD_REQUIREMENT on the pure + packing engines.

Every dynamical operation must be attention / MLP / LayerNorm / structured-linear. This greps
the step paths for forbidden force-like / ledger / variable-N patterns. (Coarse but catches the
regressions we care about: a raw 1/d² kernel, an energy book, token insert/delete.)
"""

from __future__ import annotations

import inspect
import io
import re
import tokenize

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
            src.append(_strip_comments(inspect.getsource(obj.step)))
    return "\n".join(src)


def _strip_comments(src: str) -> str:
    """Drop `#` comments so the check tests DYNAMICS CODE, not design prose.

    The forbidden patterns are *code constructs* (a 1/d² kernel, an ``energy``
    accumulator, token insert/delete). Describing the conservative forces as
    "gradients of a free energy" in a comment is faithful design commentary, not a
    ledger — it must not trip the grep. A real ``energy = ...`` in code still would.
    """
    lines = src.split("\n")
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            (sr, sc), (_, ec) = tok.start, tok.end  # comments are single-line
            lines[sr - 1] = lines[sr - 1][:sc] + lines[sr - 1][ec:]
    return "\n".join(lines)


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
