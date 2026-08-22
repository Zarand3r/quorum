"""Assert the chemistry a file was produced under, at READ time.

Every guard in this project checks a result against an independent artifact -- render against metric,
log against npz, file counts against seed counts. None of them checked that the RUN CONDITIONS were
what the analysis assumed, and that gap cost ten ticks of work: `VIVARIUM_CHI_HT` was dropped when the
`chi_TW` scan began, so runs labelled "baseline" silently used the default +0.20, at which
`chi_HT == chi_HH` and, per `field.py:91`, an ordered bilayer is not even a local minimum.

`_env_tag` had recorded the truth in every filename the whole time. The failure was that nothing read
it back. These helpers close that loop: analysis code states the chemistry it believes it is analysing
and fails loudly when the artifact disagrees.
"""

from __future__ import annotations

import re

# Values that make this model an amphiphile with leaflets that hold together. chi_HT must be NEGATIVE:
# at the +0.20 default a head is indifferent between a head and a tail neighbour.
AMPHIPHILE = {"ht": -0.25, "ww": 0.50}


def chemistry_of(name: str) -> dict[str, float]:
    """Parse the VIVARIUM_* overrides `_env_tag` wrote into a filename.

    Absent keys are absent, NOT defaulted -- a missing `ht` is the exact failure this exists to catch,
    and silently substituting 0.20 would hide it again.
    """
    out: dict[str, float] = {}
    for key, val in re.findall(r"_(ht|tw|hh|ww)(-?\d+(?:\.\d+)?)", name):
        out[key] = float(val)
    return out


def assert_chemistry(name: str, expect: dict[str, float] | None = None) -> dict[str, float]:
    """Raise unless `name` was produced under `expect` (default: the amphiphile chemistry).

    Returns the parsed chemistry so callers can log what they actually analysed.
    """
    expect = AMPHIPHILE if expect is None else expect
    got = chemistry_of(name)
    bad = {k: (v, got.get(k)) for k, v in expect.items() if got.get(k) != v}
    if bad:
        detail = ", ".join(f"{k}: expected {want}, file has {have}" for k, (want, have) in bad.items())
        raise ValueError(f"chemistry mismatch in {name!r} -- {detail}")
    return got
