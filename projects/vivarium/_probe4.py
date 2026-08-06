"""Re-measure the head_sigma scan with core-based clustering, and save states for re-analysis.

The first pass reported aggregate growth 18 -> 53 as head_sigma rose, but the cross-section showed
about eight distinct micelles while the clustering reported two components holding nearly every
lipid. Single-linkage over ALL beads percolates: one contact anywhere fuses two whole micelles, and
raising head_sigma packs 315 lipid beads plus 250 waters more tightly into the same 11x11 box, so
merging gets easier exactly as the scanned parameter rises. Size and artifact move together.

`core_sizes` clusters TAIL beads only. Two distinct micelles hold their hydrophobic cores two head
layers apart (~3.6 at head_sigma 1.8), far outside a 1.6 tail-tail cutoff, so cores cannot percolate
through touching coronas. One core = one aggregate. Both numbers are reported so the size of the
artifact is visible rather than quietly corrected.
"""
import sys
import numpy as np
from bicelle2d import build
from harness import measure
from xsection import cross_section

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"
BASE = dict(bound=11.0, kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6, repel=12.0, n_water=250, plant=False,
            n_lip=63)

def _pd(e, A, B):
    d = e.X[A][:, None, :e.pd] - e.X[B][None, :, :e.pd]
    d -= e.L * np.round(d / e.L)
    return np.linalg.norm(d, axis=2)

def _components(adj):
    n, seen, out = adj.shape[0], set(), []
    for s0 in range(n):
        if s0 in seen: continue
        st, c = [s0], 0; seen.add(s0)
        while st:
            u = st.pop(); c += 1
            for v in np.where(adj[u])[0]:
                if v not in seen: seen.add(v); st.append(v)
        out.append(c)
    return sorted(out, reverse=True)

def all_bead_sizes(e):
    """The original estimator: single-linkage over every bead. Kept only for comparison."""
    mol = e._mol
    D = _pd(e, mol.ravel(), mol.ravel())
    adj = (D < 1.6).reshape(len(mol), mol.shape[1], len(mol), mol.shape[1]).any(axis=(1, 3))
    return _components(adj)

def core_sizes(e):
    """One hydrophobic core = one aggregate. Tail beads only, so coronas cannot bridge micelles."""
    mol = e._mol
    t = mol[:, 1:]
    D = _pd(e, t.ravel(), t.ravel())
    adj = (D < 1.6).reshape(len(mol), t.shape[1], len(mol), t.shape[1]).any(axis=(1, 3))
    return _components(adj)

def exposed(e):
    mol = e._mol
    tails = mol[:, 1:].ravel()
    water = np.setdiff1d(np.arange(e.X.shape[0]), mol.ravel())
    cut = 1.3 * (e.sigma[tails][:, None] + e.sigma[water][None, :])
    return float((_pd(e, tails, water) < cut).any(axis=1).mean())

tag, kw = sys.argv[1], eval(sys.argv[2])
seed = kw.pop("seed", 7)
e = build(seed, **{**BASE, **kw})
T = 20000
while getattr(e, "_t", 0) < T:
    e.step(); e._t = getattr(e, "_t", 0) + 1

core = [s for s in core_sizes(e) if s >= 3]
allb = [s for s in all_bead_sizes(e) if s >= 3]
m = measure(e)
cmean = sum(core) / len(core) if core else 0.0
print(f"RESULT {tag:<10}{len(core):>6}{cmean:>8.1f}{(max(core) if core else 0):>8}"
      f"{len(allb):>7}{(max(allb) if allb else 0):>8}"
      f"{exposed(e):>9.3f}{m['align']:>8.3f}{m['splay']:>8.3f}"
      f"{m['packing']:>9.3f}{m['wet_frac']:>9.3f}{m['solvent_packing']:>9.3f}{m['bilayer_frac']:>9.3f}", flush=True)
np.savez_compressed(f"{ST}/{tag}.npz", X=e.X, sigma=e.sigma, mol=e._mol, L=e.L, pd=e.pd)
cross_section(e, f"{OUT}/core_{tag}",
              title=f"2-D self-assembly, {tag}, t={T}",
              sub=f"cores {len(core)} mean {cmean:.1f} largest {(max(core) if core else 0)}  "
                  f"exposed {exposed(e):.3f}  (all-bead linkage would say "
                  f"{len(allb)} / {(max(allb) if allb else 0)})")
