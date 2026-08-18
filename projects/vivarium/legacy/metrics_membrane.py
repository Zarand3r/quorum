"""Membrane self-assembly metrics — geometric, trustworthy (validated against the eye).

Unlike the aliveness gauge, a membrane is a *concrete geometric structure*, so these numbers are
verifiable by looking: if H says "tails buried" and sheetness says "ribbon", you see a bilayer.

  H (hydrophobic shielding) — mean over lipids of the lipid-fraction of the TAIL-side neighbourhood
    (tail-aligned weighting). H→1 = tails buried away from water = self-assembled. THE assembly signal.
  sheetness — largest lipid cluster's position-covariance aspect ratio: micelle ≈ 1, bilayer ribbon ≫ 1.
  n_lipid_clusters — how many separate lipid aggregates (single-linkage).

All on the periodic torus (min-image).
"""

from __future__ import annotations

import numpy as np

WATER, LIPID = 0, 1


def _min_image(diff: np.ndarray, L: float) -> np.ndarray:
    return diff - L * np.round(diff / L)


def _neighbors_within(pos: np.ndarray, L: float, radius: float):
    """(N,N) mask of neighbours within `radius` (min-image), plus unit bearings r̂_ij (i→j)."""
    d = _min_image(pos[None, :, :] - pos[:, None, :], L)      # (N,N,2): j − i
    d2 = np.einsum("ijc,ijc->ij", d, d)
    within = (d2 < radius * radius)
    np.fill_diagonal(within, False)
    dist = np.sqrt(d2 + 1e-12)
    rhat = d / dist[..., None]
    return within, rhat, d2


def hydrophobic_shielding(pos, species, orient, L, radius=1.6) -> float:
    """Mean over lipids of the lipid-fraction of the tail-side neighbourhood (tail-weighted)."""
    species = np.asarray(species)
    lip = np.where(species == LIPID)[0]
    if lip.size == 0:
        return 0.0
    within, rhat, _ = _neighbors_within(pos, L, radius)
    is_lipid = (species == LIPID).astype(np.float64)
    vals = []
    for i in lip:
        nb = within[i]
        if not nb.any():
            continue
        # tail side = bearing aligned with i's orientation (tail = +o); weight ∝ alignment⁺
        tail_w = np.maximum(0.0, rhat[i] @ orient[i]) * nb
        denom = tail_w.sum()
        if denom < 1e-9:
            continue
        vals.append(float((tail_w * is_lipid).sum() / denom))
    return float(np.mean(vals)) if vals else 0.0


def _clusters(pos, L, radius):
    within, _, _ = _neighbors_within(pos, L, radius)
    n = pos.shape[0]
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        for j in range(i + 1, n):
            if within[i, j]:
                ra, rb = find(i), find(j)
                if ra != rb:
                    parent[ra] = rb
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def sheetness(pos, species, L, radius=1.6) -> tuple[float, int]:
    """(aspect ratio of the largest lipid cluster, number of lipid clusters). Micelle≈1, ribbon≫1."""
    species = np.asarray(species)
    lip = np.where(species == LIPID)[0]
    if lip.size < 3:
        return 1.0, 0
    lip_pos = pos[lip]
    groups = _clusters(lip_pos, L, radius)
    largest = max(groups, key=len)
    if len(largest) < 3:
        return 1.0, len(groups)
    p = lip_pos[largest]
    ref = p[0]
    p = ref + _min_image(p - ref, L)      # unwrap around a member
    p = p - p.mean(0)
    cov = (p.T @ p) / len(p)
    ev = np.linalg.eigvalsh(cov)
    ev = np.clip(ev, 1e-9, None)
    return float(np.sqrt(ev[-1] / ev[0])), len(groups)


def membrane_order(pos, species, orient, L, radius=1.6) -> tuple[float, float]:
    """Over lipid neighbour pairs (min-image): (director order S = mean |o_i·o_j|, side-by-side
    fraction = mean 1−(o_i·r̂_ij)²). UNSIGNED so both leaflets of a bilayer (which are antiparallel)
    count as ordered: S→1 means every lipid shares one axis. A disordered thread has S≈½, side≈½."""
    species = np.asarray(species)
    within, rhat, _ = _neighbors_within(pos, L, radius)
    lip = (species == LIPID)
    pair = within & lip[:, None] & lip[None, :]
    ii, jj = np.where(pair)
    if ii.size == 0:
        return 0.0, 0.0
    oo = np.einsum("kc,kc->k", orient[ii], orient[jj])
    oir = np.einsum("kc,kc->k", orient[ii], rhat[ii, jj])
    S = float(np.mean(np.abs(oo)))
    side = float(np.mean(1.0 - oir ** 2))
    return S, side


def measure(pos, species, orient, L, radius=1.6) -> dict:
    H = hydrophobic_shielding(pos, species, orient, L, radius)
    aspect, nclust = sheetness(pos, species, L, radius)
    S, side = membrane_order(pos, species, orient, L, radius)
    return {"H": round(H, 3), "sheetness": round(aspect, 2), "n_lipid_clusters": nclust,
            "S": round(S, 3), "side": round(side, 3)}
