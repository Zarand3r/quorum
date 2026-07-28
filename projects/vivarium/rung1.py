"""RUNG 1 — do lipids form a MICELLE (heads out, tails in)?

PRE-REGISTERED FALSIFIER, written before running: a micelle places heads outside tails, so
<r_head> - <r_tail> measured from the aggregate centre of mass must exceed +0.35. Tail burial does
NOT count as evidence; it rises for any aggregate and produced a false positive here once already.

The distinguishing test is radial organisation, which I never ran: in a micelle the heads sit on the
outside and the tails in the core, so <r_head> must exceed <r_tail> measured from the aggregate's own
centre of mass. A blob buries both indiscriminately and the two radii coincide.
"""
import math
import numpy as np
from bilayer3d import build, metrics


def radial(e):
    mol = e._mol
    if not mol.size:
        return None
    P = e.X[:, :3]
    L = e.L
    # largest connected lipid cluster, by molecular centre
    cen = P[mol[:, 1]]
    d = cen[:, None, :] - cen[None, :, :]
    d = d - L * np.round(d / L)
    near = np.einsum("ijc,ijc->ij", d, d) < 2.2 ** 2
    np.fill_diagonal(near, False)
    seen, best = set(), []
    for s in range(len(cen)):
        if s in seen:
            continue
        stack, comp = [s], []
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k); comp.append(k)
            stack.extend(np.where(near[k])[0].tolist())
        if len(comp) > len(best):
            best = comp
    if len(best) < 4:
        return None
    idx = mol[best]
    ref = P[idx[0, 1]]
    def unwrap(pts):
        v = pts - ref
        return ref + (v - L * np.round(v / L))
    heads, mids, tails = unwrap(P[idx[:, 0]]), unwrap(P[idx[:, 1]]), unwrap(P[idx[:, 2]])
    com = np.concatenate([heads, mids, tails]).mean(0)
    rh = np.linalg.norm(heads - com, axis=1).mean()
    rt = np.linalg.norm(tails - com, axis=1).mean()
    return len(best), rh, rt


if __name__ == "__main__":
    import sys
    n_tail = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n_lip = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    e = build(seed=3, n_lip=n_lip, bound=3.4, kt=0.02, speed=0.08, repel=12.0,
              k_bond=8.0, satt=0.55, spol=0.90, plant=False, n_tail=n_tail)
    print(f"  tail beads = {n_tail}, lipids = {n_lip}, N = {e.cfg.N}")
    print("  falsifier: <r_head> - <r_tail> must exceed +0.35 to count as a micelle")
    print("  step  cluster  <r_head>  <r_tail>   head-tail   verdict")
    for t in range(0, 240001, 40000):
        r = radial(e)
        if r:
            n, rh, rt = r
            gap = rh - rt
            v = "MICELLE" if gap > 0.35 else ("weak" if gap > 0.15 else "blob (no radial order)")
            print(f"  {t:6d}   {n:3d}     {rh:6.3f}    {rt:6.3f}    {gap:+.3f}   {v}", flush=True)
        if t < 240000:
            for _ in range(40000):
                e.step()
