"""A flatness estimator that survives thermal noise, and its calibration.

`_pairing.bilayer_frac`'s `flat` term thresholds a PER-MOLECULE dot product at 0.90 (25.8 deg). At
kT=1 single-molecule tilt is comparable to that, so a planted flat bilayer that is fully intact and
laterally fluid falls from 1.000 to 0.125 (D10). The term measures thermal tilt, not shape.

Fix: average each molecule's axis over its same-leaflet neighbourhood FIRST, producing a smoothed
local normal, then compare smoothed normals between neighbouring patches.

    n_i = normalize( sum_{j in nbrs(i) + i} u_j )
    flat_i = mean_{j in nbrs(i)} ( n_i . n_j )

Uncorrelated thermal tilt averages down as 1/sqrt(z) over z neighbours, so a flat-but-noisy membrane
recovers a high score. Systematic curvature does NOT average away: inside a micelle consecutive
molecules fan by the angular step set by its radius, and that rotation is present in the smoothed
normals too. So the estimator keeps the property that made the conjunction necessary in the first
place while dropping the property that made it useless at kT>0.

Reported as raw means rather than thresholded fractions, so the separation between structures is
visible instead of being hidden behind a cutoff chosen after the fact.
"""

import sys

import numpy as np

from _pairing import _mic, _plant_bilayer, _plant_micelle

ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"


def axes(x, L, b0, nb, nh):
    head = np.stack([x[b0 + t] for t in range(nh)]).mean(axis=0)
    tail = np.stack([x[b0 + t] for t in range(nh, nb)]).mean(axis=0)
    tip = x[b0 + (nb - 1)]
    u = head - tail
    u -= L * np.round(u / L)
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    return head, tip, u


def measure(x, L, b0, nb, nh, rcut=1.5, lat=1.6):
    head, tip, u = axes(x, L, b0, nb, nh)
    dot = u @ u.T
    D = np.linalg.norm(_mic(tip, tip, L), axis=2)
    np.fill_diagonal(D, np.inf)
    H = np.linalg.norm(_mic(head, head, L), axis=2)
    paired = ((D < rcut) & (dot < -0.5) & (H > D)).any(axis=1)

    same = (H < lat) & (dot > 0.5)
    np.fill_diagonal(same, False)
    cnt = same.sum(axis=1)

    # old, per-molecule flatness -- the thing that broke
    old = np.where(cnt > 0, (dot * same).sum(axis=1) / np.maximum(cnt, 1), 0.0)

    # smoothed local normal: neighbourhood mean of the axes, including self
    inc = same.copy()
    np.fill_diagonal(inc, True)
    n = inc.astype(float) @ u
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    ndot = n @ n.T
    new = np.where(cnt > 0, (ndot * same).sum(axis=1) / np.maximum(cnt, 1), 0.0)

    ok = cnt >= 2
    if not ok.any():
        return float(paired.mean()), float("nan"), float("nan"), float(cnt.mean())
    return (float(paired.mean()), float(old[ok].mean()), float(new[ok].mean()),
            float(cnt.mean()))


def burial(x, sp, L, cut=1.0):
    """Fraction of TAIL beads with no water within `cut`, and the same for HEAD beads.

    The visible difference between a clean bilayer and a patchy aggregate is not local angular order
    -- the smoothed-normal estimator saturates at 0.95-0.98 on both -- it is whether the hydrophobic
    core is actually covered. Burial is a density measure, so thermal tilt does not touch it, and it
    is the same quantity that sets edge line tension: an exposed tail bead IS the edge energy.

    A well-organised amphiphile assembly buries tails AND solvates heads, so the two are reported
    together; burying everything just means the aggregate collapsed.
    """
    wat = x[sp == 0]
    out = []
    for s_ in (2, 1):
        b = x[sp == s_]
        if len(b) == 0 or len(wat) == 0:
            out.append(float("nan")); continue
        near = np.zeros(len(b), bool)
        chunk = max(1, int(2e7 // max(len(wat), 1)))
        for k in range(0, len(b), chunk):
            d = b[k:k + chunk, None, :] - wat[None, :, :]
            d -= L * np.round(d / L)
            near[k:k + chunk] = (np.einsum("ijc,ijc->ij", d, d) < cut * cut).any(axis=1)
        out.append(float(1.0 - near.mean()))
    return out[0], out[1]


def row(label, x, L, b0, nb, nh, sp=None):
    p, o, s, z = measure(x, L, b0, nb, nh)
    if sp is None:
        print(f"{label:34s}{p:>9.3f}{o:>10.3f}{s:>11.3f}{z:>7.1f}")
        return
    tb, hb = burial(x, sp, L)
    print(f"{label:34s}{p:>9.3f}{o:>10.3f}{s:>11.3f}{z:>7.1f}{tb:>10.3f}{hb:>9.3f}")


def load(tag):
    z = np.load(f"{ST}/{tag}.npz")
    x, L = z["x"], float(z["L"])
    if "nb" in set(z.keys()):
        nb, nh, n = int(z["nb"]), int(z.get("nh", 1)), int(z["n_amph"])
        return x, L, np.arange(n) * nb, nb, nh
    heads = np.flatnonzero(z["species"] == 1)
    return x, L, heads, int(np.median(np.diff(heads))), 1


def load_sp(tag):
    return np.load(f"{ST}/{tag}.npz")["species"]


if __name__ == "__main__":
    print(f"{'structure':34s}{'paired':>9}{'flat_old':>10}{'flat_new':>11}{'<z>':>7}"
          f"{'tailBuried':>10}{'headBur':>9}")
    print("-- synthetic poles (no thermal noise) " + "-" * 34)
    for dim in (2, 3):
        x, b0 = _plant_bilayer(dim)
        row(f"{dim}-D planted BILAYER", x % 60.0, 60.0, b0, 4, 1)
        x, b0, M = _plant_micelle(dim)
        row(f"{dim}-D planted MICELLE (M={M})", x % 20.0, 20.0, b0, 4, 1)
    print("-- real states " + "-" * 56)
    for tag, label in (("flat_therm_t0", "planted flat bilayer t=0"),
                       ("flat_therm_t6000", "planted flat bilayer THERMALIZED"),
                       ("ves_planted_R9", "planted R=9 vesicle THERMALIZED"),
                       ("ves_planted_R7.5", "planted R=7.5 vesicle THERMALIZED"),
                       ("ves_planted_R6", "planted R=6 vesicle THERMALIZED"),
                       ("sl_f28_N12000_s1", "EMERGENT 3-D slab"),
                       ("sa_phi15_N12000_s1", "EMERGENT 3-D (not a clean bilayer)"),
                       ("big_phi20_nb3_da15_s1", "EMERGENT 2-D ribbons")):
        try:
            x, L, b0, nb, nh = load(tag)
            row(label, x, L, b0, nb, nh, load_sp(tag))
        except FileNotFoundError:
            print(f"{label:34s}{'(missing)':>9}")
