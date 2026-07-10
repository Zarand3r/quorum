"""The conservation ledger (P1) — the spine of the whole substrate.

The conserved quantity is total energy/matter, partitioned into three books:
  - ``pool``       : unharvested resource in the environment
  - ``sum(e)``     : energy held by living tokens
  - ``dissipated`` : cumulative energy lost to heat (metabolism, motion, harvest
                     inefficiency, the last energy of the dead)

The system is closed except for injection: across any tick the total may increase
ONLY by what was injected. Everything else (harvest, movement, death, reproduction)
merely moves energy *between* the three books. ``ledger_residual`` is the check.
"""

from __future__ import annotations

import numpy as np


def book_total(pool: float, e: np.ndarray, dissipated: float) -> float:
    """Total conserved quantity across the three books."""
    return float(pool) + float(np.sum(e)) + float(dissipated)


def ledger_residual(
    total_before: float,
    total_after: float,
    injected: float,
) -> float:
    """Signed conservation error for a tick: 0 ⇔ energy is conserved.

    total_after - total_before must equal exactly what was injected.
    """
    return total_after - total_before - injected
