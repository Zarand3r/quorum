"""Annealed 2-D self-assembly: can a cooling schedule cross the nucleation barrier?

The 2-D lamellar phase is STABLE when planted (08-02c), so reaching it from disorder is a kinetics
question, not a thermodynamic one. Assembly stalls just short (08-02d: splay flattens at ~0.35
against a required 0.30, spanning 0.64-0.73 against 0.80) with packing healthy throughout, which is
the shape of a nucleation problem rather than a collapse.

Two independent pieces of evidence say the system is frozen rather than finished. Coarsening runs
(08-01o) show the sphere -> rod -> lamellar progression START and then arrest: aggregates fuse 8 -> 5,
mean size 7.4 -> 12.2, align climbs to 0.813, and there it stops. And the coexistence run at repel 24
showed NOTHING transferring between a planted strip and a micelle -- no lipid exchange between
aggregates at kT=0.02. Frozen exchange is exactly what stops coarsening past ~12-18.

anneal() has been implemented in this project for months and never used for 2-D self-assembly. Its
own docstring names the trap: too cold from the start and the system freezes into whatever
disordered arrangement it began in. hot == cold reproduces a fixed-kT run exactly, so it is the
honest control.
"""
import sys
import numpy as np
from bicelle2d import build
from harness import measure
from experiment import anneal, stage3
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
T = int(kw.pop("steps", 60000))
hot = float(kw.pop("hot", 0.02))
e = build(seed, **{**BASE, **kw})
anneal(e, T, hot=hot, cold=BASE["kt"])

core = [s for s in core_sizes(e) if s >= 3]
allb = [s for s in all_bead_sizes(e) if s >= 3]
m = measure(e)
cmean = sum(core) / len(core) if core else 0.0
print(f"RESULT {tag:<10}{len(core):>6}{cmean:>8.1f}{(max(core) if core else 0):>8}"
      f"{len(allb):>7}{(max(allb) if allb else 0):>8}"
      f"{exposed(e):>9.3f}{m['align']:>8.3f}{m['splay']:>8.3f}"
      f"{m['packing']:>9.3f}{m['spanning']:>10.3f}"
      f"{('STAGE3' if stage3(m) else '-'):>9}", flush=True)
np.savez_compressed(f"{ST}/{tag}.npz", X=e.X, sigma=e.sigma, mol=e._mol, L=e.L, pd=e.pd)
cross_section(e, f"{OUT}/core_{tag}",
              title=f"2-D self-assembly, {tag}, t={T}",
              sub=f"cores {len(core)} mean {cmean:.1f} largest {(max(core) if core else 0)}  "
                  f"exposed {exposed(e):.3f}  (all-bead linkage would say "
                  f"{len(allb)} / {(max(allb) if allb else 0)})")
