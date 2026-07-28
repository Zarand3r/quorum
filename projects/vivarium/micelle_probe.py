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
    sphericity  ratio of the smallest to largest principal moment of the cluster. Near 1 = ball
              (micelle), near 0 = sheet or rod. Tells you whether a RADIAL measure means anything.
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
        ev = np.linalg.eigvalsh(c.T @ c / len(c))
        spher = float(ev[0] / max(ev[-1], 1e-9))
        res.append((len(comp), outward, shell, spher))
    return res


def report(e, tag):
    rs = probe(e)
    if not rs:
        print(f"  {tag:>8s}  no cluster of 8+ molecules")
        return
    for n, o, sh, sp in rs[:3]:
        verdict = "MICELLE" if (o > 0.45 and sh > 0.75) else ("partial" if o > 0.2 else "no radial order")
        print(f"  {tag:>8s}  n={n:3d}  outward={o:+.3f}  shell={sh:.2f}  sphericity={sp:.2f}   {verdict}")
