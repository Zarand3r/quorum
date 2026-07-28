"""What do the micelle metrics read on RANDOM molecules? The null baseline none of them had.

`outward` is <u_i . rhat_i>, where u is the tail->head axis and rhat is the outward direction AT THE
HEAD. The head's position is itself tail + L*u, so u appears on both sides of the dot product. That
is a self-correlation, and it biases the statistic positive even when orientations are random. A
metric's threshold means nothing until its null is known, so this measures the null directly:
molecules with random centres in a ball and INDEPENDENT random orientations, scored by the same math.
"""

import numpy as np

BOND = 0.9


def null(n_mol=16, n_bead=5, radius=2.5, trials=4000, seed=0):
    rng = np.random.default_rng(seed)
    out = np.empty(trials); cyl = np.empty(trials); shl = np.empty(trials)
    fix = np.empty(trials)
    for t in range(trials):
        v = rng.standard_normal((n_mol, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        cen = v * radius * rng.random((n_mol, 1)) ** (1 / 3)      # uniform in a ball
        u = rng.standard_normal((n_mol, 3))                        # INDEPENDENT orientation
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        half = (n_bead - 1) / 2.0
        beads = np.concatenate([cen + (half - b) * BOND * u for b in range(n_bead)])
        heads, tails = cen + half * BOND * u, cen - half * BOND * u
        com = beads.mean(0)
        r = heads - com
        rhat = r / np.maximum(np.linalg.norm(r, axis=1, keepdims=True), 1e-9)
        out[t] = (u * rhat).sum(1).mean()
        rc = cen - com                                             # rhat from the molecular CENTRE
        rc /= np.maximum(np.linalg.norm(rc, axis=1, keepdims=True), 1e-9)
        fix[t] = (u * rc).sum(1).mean()
        c = beads - com
        ev, evec = np.linalg.eigh(c.T @ c / len(c))
        ax = evec[:, 2]
        rp = r - np.outer(r @ ax, ax); up = u - np.outer(u @ ax, ax)
        rp /= np.maximum(np.linalg.norm(rp, axis=1, keepdims=True), 1e-9)
        up /= np.maximum(np.linalg.norm(up, axis=1, keepdims=True), 1e-9)
        cyl[t] = (up * rp).sum(1).mean()
        shl[t] = (np.linalg.norm(heads - com, axis=1) > np.linalg.norm(tails - com, axis=1)).mean()
    return out, cyl, shl, fix


if __name__ == "__main__":
    print("NULL MODEL: random centres, INDEPENDENT random orientations. True radial order is ZERO.\n")
    print("  %-8s %-14s %-14s %-8s %s" % ("radius", "outward", "cyl", "shell", "outward_c (FIXED)"))
    for radius in (1.5, 2.5, 4.0, 8.0):
        o, c, s, f = null(radius=radius)
        print("  %-8.1f %+.3f+/-%.3f  %+.3f+/-%.3f  %.3f    %+.3f +/- %.3f (p95 %+.3f)"
              % (radius, o.mean(), o.std(), c.mean(), c.std(), s.mean(),
                 f.mean(), f.std(), np.percentile(f, 95)))
    print("\n  outward and cyl build rhat from the HEAD, whose position is cen + (L/2)u, so u sits on")
    print("  both sides of the dot product and the statistic is biased positive. outward_c builds")
    print("  rhat from the molecular CENTRE, which is independent of u under the null, so its")
    print("  baseline is zero and a threshold can actually be read against it.")
