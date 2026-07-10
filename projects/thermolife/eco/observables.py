"""Read-only observables (IMPLEMENTATION_PLAN.md Step 8; EMERGENCE_PLAN §7).

MEASURED, NEVER REWARDED (P2): nothing in this module may be imported by the
dynamics (eco/engine.py, eco/interaction.py, eco/policies.py) or fed into any
fitness/reward. A structural test enforces the import direction.
"""

from __future__ import annotations

import numpy as np


def attention_entropy(a: np.ndarray) -> float:
    """Mean row entropy of the interaction graph (nats). High = diffuse
    interaction; near 0 = frozen/self-only. The non-settling observable."""
    if a.size == 0:
        return 0.0
    p = np.maximum(a, 1e-12)
    return float(-np.mean(np.sum(p * np.log(p), axis=1)))


def transfer_on_edges(transfer: np.ndarray, a: np.ndarray, thresh: float = 0.05) -> float:
    """Fraction of transferred energy that rides interaction edges with
    A_ij > thresh — the 'energy transport follows attention' observable."""
    total = float(transfer.sum())
    if total <= 0.0:
        return 0.0
    on = float(transfer[a > thresh].sum())
    return on / total


def interaction_degree(a: np.ndarray, thresh: float = 0.05) -> float:
    """Mean number of non-self partners a token interacts with above threshold."""
    if a.size == 0:
        return 0.0
    off = a * (1.0 - np.eye(a.shape[0]))
    return float(np.mean(np.sum(off > thresh, axis=1)))
