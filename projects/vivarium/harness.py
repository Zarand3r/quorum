"""One validated measurement chokepoint. Nothing else should compute geometry on a periodic system.

Seven measurement defects in this project came from geometry computed on raw coordinates. The worst
were: an order parameter that correlated with itself (null +0.669 where 0 was assumed), and bond
lengths measured without minimum image, which reported 13.3 in a box of 10 and sent three separate
diagnoses down the wrong path. The engine's own forces were always right; only the measurements were
wrong.

So every quantity here goes through two rules:

  1. UNWRAP FIRST. On a periodic axis, a raw difference is meaningless: an aggregate straddling the
     boundary yields a covariance, a midplane and a bond length that are all garbage. `unwrap()` is
     the only place a periodic difference is taken.
  2. DISQUALIFY, DO NOT INTERPRET. If the molecule is deformed or the integrator is overshooting, the
     structural numbers describe nothing, so `measure()` returns `ok=False` and the caller must throw
     the sample away rather than read `aspect` off a broken configuration.

Every metric here has been calibrated against BOTH controls -- a planted structure must score high AND
a random configuration must score at the null. A positive control alone cannot catch a self-correlated
statistic, which is how three micelle claims survived for a day.

    lamellar  fraction of lipids whose HEAD lies farther from the aggregate midplane than its OWN
              tails. Planted bilayer ~1.0, random ~0.5. NOTE it reads 1.0 on a collapsed droplet too,
              so it is necessary and NOT sufficient -- always read it with `aspect`.
    aspect    L1/L3 of the largest cluster's covariance, unwrapped. A slab or ribbon is thin in one
              axis (low); a droplet is round (~0.8+). This is the discriminator a droplet cannot fake.
"""

from __future__ import annotations

import numpy as np

BOND_REST = 1.0
BOND_MAX = 1.25          # beyond this the molecule is deformed and nothing structural is admissible
DISP_MAX = 0.05          # per-step displacement above which the integrator is overshooting


def _periodic_axes(e):
    walls = tuple(getattr(e, "wall_axes", ()) or ())
    return np.array([ax not in walls for ax in range(e.pd)])


def delta(e, a, b):
    """The ONLY place a periodic difference is taken. Minimum image on periodic axes only."""
    d = e.X[a, :e.pd] - e.X[b, :e.pd]
    free = _periodic_axes(e)
    d[:, free] -= e.L * np.round(d[:, free] / e.L)
    return d


def unwrap(e, idx, ref=None):
    """Positions of `idx` made contiguous around `ref`, so covariance and midplane are meaningful."""
    ref = idx[0] if ref is None else ref
    d = e.X[idx, :e.pd] - e.X[ref, :e.pd]
    free = _periodic_axes(e)
    d[:, free] -= e.L * np.round(d[:, free] / e.L)
    return e.X[ref, :e.pd] + d


def bond_stats(e):
    """(mean, max, fraction stretched) over EVERY backbone bond, with minimum image.

    Measuring only the first bond hid the problem once already: bonds stretch unevenly along a chain,
    and the head-tail bond is the least affected.
    """
    mol = e._mol
    if not mol.size:
        return 0.0, 0.0, 0.0
    ds = [np.linalg.norm(delta(e, mol[:, k], mol[:, k + 1]), axis=1)
          for k in range(mol.shape[1] - 1)]
    d = np.concatenate(ds)
    return float(d.mean()), float(d.max()), float((d > BOND_MAX).mean())


def largest_cluster(e, cutoff=2.2):
    """Molecule indices of the biggest connected aggregate, joined with minimum image.

    Shape must be measured PER CLUSTER: a global covariance over several droplets reports the
    arrangement of droplets, not the shape of any of them.
    """
    mol = e._mol
    n = len(mol)
    if n == 0:
        return np.zeros(0, dtype=int)
    cen = mol[:, mol.shape[1] // 2]
    d = e.X[cen, :e.pd][:, None, :] - e.X[cen, :e.pd][None, :, :]
    free = _periodic_axes(e)
    d[..., free] -= e.L * np.round(d[..., free] / e.L)
    near = np.einsum("ijc,ijc->ij", d, d) < cutoff ** 2
    np.fill_diagonal(near, False)
    seen, best = set(), []
    for s in range(n):
        if s in seen:
            continue
        stack, comp = [s], []
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            comp.append(k)
            stack.extend(np.where(near[k])[0].tolist())
        if len(comp) > len(best):
            best = comp
    return np.array(sorted(best), dtype=int)


def measure(e, prev_X=None):
    # prev_X MUST be from exactly one step earlier: DISP_MAX is a per-step bound.
    """All admissible structure in one call.

    Returns a dict. `ok` is False when the molecule is deformed or the integrator is overshooting; in
    that case the structural fields describe nothing and must not be read.
    """
    mol = e._mol
    bmean, bmax, bfrac = bond_stats(e)
    out = {"bond_mean": bmean, "bond_max": bmax, "bond_frac": bfrac,
           "disp": 0.0, "ok": True, "why": "", "n_cluster": 0,
           "lamellar": float("nan"), "aspect": float("nan"), "aspect2": float("nan")}

    if prev_X is not None:
        d = e.X[:, :e.pd] - prev_X[:, :e.pd]
        free = _periodic_axes(e)
        d[:, free] -= e.L * np.round(d[:, free] / e.L)
        out["disp"] = float(np.linalg.norm(d, axis=1).max())

    if bfrac > 0.02:
        out["ok"], out["why"] = False, f"molecule deformed (bond mean {bmean:.2f}, {bfrac:.0%} > {BOND_MAX})"
    elif out["disp"] > DISP_MAX:
        out["ok"], out["why"] = False, f"integrator overshooting ({out['disp']:.3f}/step)"

    comp = largest_cluster(e)
    out["n_cluster"] = int(len(comp))
    if len(comp) < 6:
        out["ok"], out["why"] = False, "no aggregate"
        return out

    idx = mol[comp]
    P = unwrap(e, idx.ravel(), ref=idx[0, 0])
    c = P - P.mean(0)
    ev = np.linalg.eigvalsh(c.T @ c / len(c))
    out["aspect"] = float(ev[0] / max(ev[-1], 1e-12))
    if e.pd == 3:
        out["aspect2"] = float(ev[1] / max(ev[-1], 1e-12))

    nb = idx.shape[1]
    Pm = P.reshape(len(comp), nb, e.pd)
    thin = np.linalg.eigh(c.T @ c / len(c))[1][:, 0]
    mid = P.mean(0)
    h = np.abs((Pm[:, 0] - mid) @ thin)
    t = np.abs((Pm[:, 1:] - mid[None, None, :]) @ thin).mean(axis=1)
    out["lamellar"] = float((h > t).mean())
    return out


def header():
    return ("   step  lamellar  aspect  aspect2  n_clu  bond  disp   status")


def line(t, m):
    st = "ok" if m["ok"] else f"DISQUALIFIED: {m['why']}"
    lam = "  n/a " if np.isnan(m["lamellar"]) else f"{m['lamellar']:6.3f}"
    a1 = "  n/a" if np.isnan(m["aspect"]) else f"{m['aspect']:5.2f}"
    a2 = "  n/a" if np.isnan(m["aspect2"]) else f"{m['aspect2']:5.2f}"
    return (f"  {t:6d}  {lam}  {a1}   {a2}    {m['n_cluster']:4d}  {m['bond_mean']:.2f}  "
            f"{m['disp']:.3f}  {st}")
