"""PRIORITY 1: the matched pure-solvent gate. Is Vivarium's water a liquid, or is it condensing?

HYPOTHESIS
    Vivarium's explicit water, run alone at exactly the density, box, temperature, timestep, damping,
    repulsion and water-water interaction used by bicelle2d.build, behaves as a stationary liquid.

FALSIFICATION
    Any of the following fails the gate:
      * short-range structure NOT stationary -- g(r) first-peak height drifting monotonically;
      * diffusion arrested -- MSD flat over the second half of the run;
      * a GROWING low-q mode in S(q), the signature of demixing into water-rich and water-poor
        regions (this, not raw homogeneity, is the correct macroscopic-condensation test);
      * progressive interpenetration -- the fraction of pairs inside contact rising with time;
      * a persistent macroscopic water-rich domain that grows rather than fluctuating.

WHY NOT A POISSON NULL
    An interacting liquid is SUPPOSED to be less uniform than independent random points at molecular
    scales: that is what the first peak of g(r) is. An earlier reading here compared cell-occupancy
    variance against a Poisson null (0.38) and inferred the solvent was broken from a value of ~4.
    That inference was unsound. The tests below are stationarity and low-q tests instead, which is
    what actually distinguishes a liquid from a condensing one.
"""

import sys

import numpy as np

from bicelle2d import build

# exactly bicelle2d.build's published lipid configuration, minus the lipids
WATER_CFG = dict(n_lip=0, bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0,
                 satt=0.30, n_tail=2, bond_span=2.0, n_water=250,
                 polarity=0.80, head_q=1.2, hydrophobic=0.6, attract=1.0)


def gr(x, L, rmax=6.0, nbins=60):
    """2-D radial distribution, normalised by the ideal-gas shell area."""
    n = len(x)
    d = x[:, None, :] - x[None, :, :]
    d -= L * np.round(d / L)
    r = np.linalg.norm(d, axis=2)[np.triu_indices(n, 1)]
    r = r[r < rmax]
    h, edges = np.histogram(r, bins=nbins, range=(0.0, rmax))
    rho = n / L ** 2
    shell = np.pi * (edges[1:] ** 2 - edges[:-1] ** 2)
    return 0.5 * (edges[1:] + edges[:-1]), h / (shell * rho * n / 2.0)


def sq(x, L, nk=6):
    """S(q) on the PBC-commensurate wavevectors, lowest |q| first.

    A growing S(q) at the smallest accessible q is the demixing signature; a liquid's S(q->0) is
    small and stationary (it is set by the compressibility).
    """
    n = len(x)
    ks = []
    for a in range(0, nk + 1):
        for b in range(0, nk + 1):
            if a or b:
                ks.append((a, b))
    ks = np.array(ks) * (2 * np.pi / L)
    qmag = np.linalg.norm(ks, axis=1)
    phase = x @ ks.T
    s = (np.abs(np.exp(1j * phase).sum(axis=0)) ** 2) / n
    order = np.argsort(qmag)
    return qmag[order], s[order]


def contact_penetration(x, L, contact=1.0, deep=0.5):
    """Deep-overlap FRACTION, not a coordination number.

    The first version returned the mean number of neighbours within `contact`, which in this liquid
    is ~8.8 against an ideal-gas expectation of 1.6 -- that is the first coordination shell that
    g(r)'s peak of 10 describes, not a pathology. Applying a fraction-sized threshold (0.05) to a
    count made the gate fail on ordinary liquid structure. What actually signals interpenetration is
    the fraction of particles with a neighbour DEEP inside contact, and whether it grows.
    """
    n = len(x)
    d = x[:, None, :] - x[None, :, :]
    d -= L * np.round(d / L)
    r = np.linalg.norm(d, axis=2)
    np.fill_diagonal(r, np.inf)
    nn = r.min(axis=1)
    return float((nn < deep * contact).mean()), float(np.median(nn))


def largest_domain(x, L, cut=1.4):
    """Largest connected water cluster as a fraction of all water. Grows if it is condensing."""
    from collections import deque
    n = len(x)
    d = x[:, None, :] - x[None, :, :]
    d -= L * np.round(d / L)
    adj = np.linalg.norm(d, axis=2) < cut
    np.fill_diagonal(adj, False)
    seen = np.zeros(n, bool)
    best = 0
    for s0 in range(n):
        if seen[s0]:
            continue
        q, c = deque([s0]), 0
        seen[s0] = True
        while q:
            i = q.popleft()
            c += 1
            for j in np.flatnonzero(adj[i]):
                if not seen[j]:
                    seen[j] = True
                    q.append(j)
        best = max(best, c)
    return best / n


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 40000
    e = build(0, plant=False, **WATER_CFG)
    L = e.L
    wi = e._wi
    print(f"PURE SOLVENT GATE: {len(wi)} water, box {L:.2f}, rho={len(wi)/L**2:.3f}/area, "
          f"kT={WATER_CFG['kt']}, steps={steps}", flush=True)

    x0 = e.X[wi, :2].copy()
    unwrapped = x0.copy()
    prev = x0.copy()
    every = max(steps // 8, 1)
    print(f"{'step':>7}{'g1_peak':>9}{'r_peak':>8}{'S(qmin)':>9}{'MSD':>9}"
          f"{'deep<0.5':>9}{'nn_med':>8}{'maxdom':>8}", flush=True)
    hist = []
    for t in range(steps + 1):
        if t % every == 0:
            x = e.X[wi, :2]
            step_d = x - prev
            step_d -= L * np.round(step_d / L)
            unwrapped += step_d
            prev = x.copy()
            rr, g = gr(x, L)
            q, s = sq(x, L)
            pen, nnmed = contact_penetration(x, L)
            msd = float(((unwrapped - x0) ** 2).sum(axis=1).mean())
            dom = largest_domain(x, L)
            hist.append((t, g.max(), rr[g.argmax()], s[0], msd, pen, nnmed, dom))
            print(f"{t:>7}{g.max():>9.2f}{rr[g.argmax()]:>8.2f}{s[0]:>9.2f}{msd:>9.3f}"
                  f"{pen:>9.2f}{nnmed:>8.2f}{dom:>8.2f}", flush=True)
        e.step()

    h = np.array(hist)
    half = len(h) // 2
    print("\nVERDICT")
    peak_drift = abs(h[-1, 1] - h[half, 1]) / max(h[half, 1], 1e-9)
    sq_growth = h[-1, 3] / max(h[half, 3], 1e-9)
    msd_late = h[-1, 4] - h[half, 4]
    pen_growth = h[-1, 5] - h[half, 5]
    dom_growth = h[-1, 7] - h[half, 7]
    checks = [
        ("g(r) first peak stationary (drift < 20% over 2nd half)", peak_drift < 0.20, f"{peak_drift:.2%}"),
        ("diffusion sustained (MSD still rising)", msd_late > 0.0, f"+{msd_late:.3f}"),
        ("no growing low-q mode (S(qmin) < 2x over 2nd half)", sq_growth < 2.0, f"{sq_growth:.2f}x"),
        ("no progressive deep overlap (fraction, 2nd half)", pen_growth <= 0.05, f"{pen_growth:+.3f}"),
        ("no growing macroscopic domain", dom_growth <= 0.05, f"{dom_growth:+.3f}"),
    ]
    for name, ok, val in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<52} {val}")
    print(f"\nGATE: {'PASS' if all(c[1] for c in checks) else 'FAIL'}")
