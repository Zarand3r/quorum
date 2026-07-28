"""Measure micellar order properly, with three independent tests instead of one fragile one.

The previous metric was `<r_head> - <r_tail>`: a difference of two mean radii. That is a bad
estimator. It differences two large numbers so it is noisy, it assumes the aggregate is spherical
and centred, and if the cluster cutoff merges two separate micelles their common centre of mass
sits BETWEEN them and every radial quantity is scrambled.

These three are better because each averages over molecules rather than differencing averages:

    outward   <u_i . r_hat_i>, the per-molecule alignment of the head->tail axis with the outward
              radial direction. +1 = every head points out, 0 = no radial order. Bounded, and the
              mean of N molecule-level terms rather than a difference of two means.
    shell     fraction of molecules whose HEAD bead is farther from the cluster centre than its own
              TAIL beads. A per-molecule yes/no, so it is robust to cluster shape.
    shape     full classification from all three principal moments L1<=L2<=L3, because the
              smallest/largest ratio alone CANNOT tell a rod from a disc (both give a small ratio)
              and a bicelle is a disc:
                  sphere  L1/L3 high            a spherical micelle
                  disc    L2/L3 high, L1/L3 low a BICELLE, the target
                  rod     L2/L3 low             a cylindrical micelle
    cyl       <u_perp . rhat_perp>, the same alignment measured in the plane PERPENDICULAR to the
              cluster's long axis. `outward` is measured from the centroid, so on an elongated
              aggregate the molecules near the two ends are radial along the LONG axis and their
              head-out order is invisible to it. A cylindrical micelle has heads out in the
              perpendicular plane only, which is exactly what this isolates. On a sphere it agrees
              with `outward`; on a rod it is the honest reading.
"""
import numpy as np


def clusters(e, cutoff=2.2):
    mol = e._mol
    if not mol.size:
        return []
    cen = e.X[mol[:, 1], :3]
    d = cen[:, None, :] - cen[None, :, :]
    d = d - e.L * np.round(d / e.L)
    near = np.einsum("ijc,ijc->ij", d, d) < cutoff ** 2
    np.fill_diagonal(near, False)
    seen, out = set(), []
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
        out.append(comp)
    return sorted(out, key=len, reverse=True)


def probe(e, min_size=8):
    mol, L = e._mol, e.L
    res = []
    for comp in clusters(e):
        if len(comp) < min_size:
            continue
        idx = mol[comp]
        ref = e.X[idx[0, 1], :3]
        def unwrap(p):
            v = p - ref
            return ref + (v - L * np.round(v / L))
        heads = unwrap(e.X[idx[:, 0], :3])
        tails = unwrap(e.X[idx[:, -1], :3])
        allb = np.concatenate([unwrap(e.X[idx[:, b], :3]) for b in range(idx.shape[1])])
        com = allb.mean(0)
        r = heads - com
        rn = np.linalg.norm(r, axis=1, keepdims=True)
        rhat = r / np.maximum(rn, 1e-9)
        u = heads - tails
        u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)
        outward = float((u * rhat).sum(1).mean())
        shell = float((np.linalg.norm(heads - com, axis=1)
                       > np.linalg.norm(tails - com, axis=1)).mean())
        c = allb - com
        ev, evec = np.linalg.eigh(c.T @ c / len(c))    # ascending: L1 <= L2 <= L3
        a1, a2 = float(ev[0] / max(ev[2], 1e-9)), float(ev[1] / max(ev[2], 1e-9))
        ax = evec[:, 2]                                 # the cluster's long axis
        rp = r - np.outer(r @ ax, ax)
        up = u - np.outer(u @ ax, ax)
        rp /= np.maximum(np.linalg.norm(rp, axis=1, keepdims=True), 1e-9)
        up /= np.maximum(np.linalg.norm(up, axis=1, keepdims=True), 1e-9)
        cyl = float((up * rp).sum(1).mean())
        if a1 > 0.55:
            shape = "sphere"
        elif a2 > 0.55:
            shape = "DISC"                              # two long axes, one short => a bicelle
        else:
            shape = "rod"
        res.append((len(comp), outward, shell, cyl, a1, a2, shape))
    return res


def report(e, tag):
    rs = probe(e)
    if not rs:
        print(f"  {tag:>8s}  no cluster of 8+ molecules", flush=True)
        return
    for n, o, sh, cy, a1, a2, shape in rs[:2]:
        # on an elongated cluster the honest radial reading is the perpendicular one
        best = cy if shape == "rod" else o
        if best > 0.45 and sh > 0.70:
            v = {"DISC": "BICELLE", "sphere": "MICELLE"}.get(shape, "CYLINDRICAL MICELLE")
        else:
            v = "partial" if best > 0.2 else "no radial order"
        print(f"  {tag:>8s}  n={n:3d}  outward={o:+.3f}  cyl={cy:+.3f}  shell={sh:.2f}  "
              f"L1/L3={a1:.2f} L2/L3={a2:.2f} {shape:6s}  {v}", flush=True)
