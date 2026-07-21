"""Read-only aggregation metrics — is it MATTER (compact, conserved) or a GAS (fills the box)?

Measured, never optimized (measure-don't-reward). These turn "does it just spread to fill the
space?" into numbers, per the M0 milestone:

  * compactness  — radius of gyration Rg of the (largest) aggregate, normalised by the box
    half-size. A GAS fills the box → Rg/box ~ O(1) and GROWS with the box. A DROPLET → Rg
    bounded and box-INDEPENDENT. The decisive test: run at 1× and 2× box; a droplet's Rg is
    unchanged, a gas's Rg scales with the box.
  * occupancy    — fraction of the domain within one interaction radius of some agent. Gas → ~1
    (fills everything); droplet → < 1 (empty space around it).
  * n_clusters   — connected components at the interaction radius (single-linkage). Coalescence
    drives this toward 1.
  * conservation — total covered area / (N × per-agent area). ~1 ⇒ sum of parts (no magic growth
    or overlap); ≫1 ⇒ spread out; ≪1 ⇒ overlapping/collapsed.

All operate on positions on the periodic torus.
"""

from __future__ import annotations

import numpy as np


def _pairwise_d2(pos: np.ndarray, L: float) -> np.ndarray:
    d = pos[:, None, :] - pos[None, :, :]
    d = d - L * np.round(d / L)                    # minimum image on the torus
    return np.einsum("ijc,ijc->ij", d, d)


def _clusters(d2: np.ndarray, radius: float) -> list[list[int]]:
    """Single-linkage connected components at `radius` (union-find)."""
    n = d2.shape[0]
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    adj = d2 <= radius * radius
    for i in range(n):
        for j in range(i + 1, n):
            if adj[i, j]:
                ra, rb = find(i), find(j)
                if ra != rb:
                    parent[ra] = rb
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def _rg(pos: np.ndarray, members: list[int], L: float) -> float:
    """Radius of gyration of a cluster, computed on the torus (unwrap to the first member)."""
    p = pos[members]
    ref = p[0]
    d = p - ref
    d = d - L * np.round(d / L)                     # unwrap around ref
    p = ref + d
    c = p.mean(0)
    return float(np.sqrt(np.mean(np.sum((p - c) ** 2, axis=1))))


def measure(pos: np.ndarray, L: float, radius: float, agent_r: float = 0.5) -> dict:
    """All aggregation metrics for one frame of positions (N,2) on an L-periodic torus."""
    n = pos.shape[0]
    d2 = _pairwise_d2(pos, L)
    groups = _clusters(d2, radius)
    largest = max(groups, key=len)
    box_half = L / 2.0

    rg = _rg(pos, largest, L)
    # occupancy: fraction of a grid within `radius` of any agent (Monte-Carlo on a lattice).
    g = 40
    xs = (np.arange(g) + 0.5) / g * L - box_half
    gx, gy = np.meshgrid(xs, xs)
    grid = np.stack([gx.ravel(), gy.ravel()], axis=1)
    gd = grid[:, None, :] - pos[None, :, :]
    gd = gd - L * np.round(gd / L)
    near = (np.einsum("gac,gac->ga", gd, gd) <= radius * radius).any(axis=1)
    occupancy = float(near.mean())

    covered = np.pi * agent_r ** 2 * len(largest)   # sum of member areas
    hull_area = np.pi * (2.0 * rg) ** 2             # rough area of the aggregate (disk ~2·Rg)
    conservation = covered / hull_area if hull_area > 0 else 0.0

    return {
        "rg": rg,
        "rg_over_box": rg / box_half,
        "occupancy": occupancy,
        "n_clusters": len(groups),
        "largest_frac": len(largest) / n,
        "conservation": float(conservation),
    }
