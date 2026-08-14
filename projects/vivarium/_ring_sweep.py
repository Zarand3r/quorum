"""PRIORITY 2: at curvature ZERO, is there ANY native Vivarium bilayer ring that stays hollow?

HYPOTHESIS
    Vivarium's native lipid chemistry can sustain a hollow two-leaflet ring, provided the ring is
    large enough that its lumen exceeds the molecular length. Spontaneous curvature would then be a
    closure/pathway control, not the source of hollowness.

FALSIFICATION
    If every planted ring from N=50 to N=120 either opens or fills its lumen at curvature 0, the
    native packing cannot support the target phase and tuning curvature is pointless. The next
    subject would be excluded volume and chain geometry, not curvature.

The ring is planted directly rather than added to bicelle2d.build, so the validated builder is
untouched. Two leaflets share a tail core at R_mid: the outer leaflet's heads point outward at
R_mid + (nb-1)*BOND_REST, the inner leaflet's heads point inward at R_mid - (nb-1)*BOND_REST.

MEASUREMENT NOTE
    A scalar alignment number cannot distinguish a proper bilayer from an inverted one -- that has
    already produced a wrong conclusion here (align 0.904 on an inverted membrane). So the readout is
    the joint distribution P(r, s) with s_i = u_i . (x_i - c)/|x_i - c|, u pointing tail-centre ->
    head. A real bilayer ring has TWO radial populations of opposite sign: inner leaflet s < 0,
    outer leaflet s > 0. Radial density profiles of head, tail and water are reported alongside, and
    a vesicle must show outer water -> outer heads -> tail core -> inner heads -> lumen water.
"""

import sys

import numpy as np

from bicelle2d import build
from fig2d import render, largest_cluster
from polar_pack import BOND_REST

CFG = dict(bound=16.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
           n_tail=2, bond_span=2.0, polarity=0.80, head_q=1.2, hydrophobic=0.6, attract=1.0)


def plant_ring(e, n_lip, nb):
    """Two leaflets sharing a tail core. Returns the midplane radius actually used."""
    mol = e._mol
    lipid_len = (nb - 1) * BOND_REST
    # split so both leaflets sit at their natural arc spacing: n_out/n_in = R_out/R_in
    # with R_out = R_mid + lipid_len and R_in = R_mid - lipid_len. Solve for R_mid given n_lip
    # at one lipid per BOND_REST of arc.
    R_mid = n_lip * BOND_REST / (4.0 * np.pi)
    R_out, R_in = R_mid + lipid_len, max(R_mid - lipid_len, 0.4)
    n_out = int(round(n_lip * R_out / (R_out + R_in)))
    n_in = n_lip - n_out
    k = 0
    for count, R_head, sgn in ((n_out, R_out, +1.0), (n_in, R_in, -1.0)):
        if count <= 0:
            continue
        th = (np.arange(count) + 0.5) / count * 2 * np.pi
        rhat = np.stack([np.cos(th), np.sin(th)], axis=1)
        idx = mol[k:k + count]
        for bead in range(nb):
            # bead 0 is the head at R_head; beads run inward toward the shared core
            rr = R_head - sgn * bead * BOND_REST
            e.X[idx[:, bead], :2] = rhat * rr
        # head_phi is per-LIPID, not per-bead; indexing it with bead ids overruns it
        e.head_phi[k:k + count] = th if sgn > 0 else th + np.pi
        k += count
    return R_mid, n_out, n_in


def profile(e, n_lip, nb):
    """Radial head/tail/water density, the P(r,s) leaflet split, and lumen occupancy."""
    mol = e._mol
    P = e.X[:, :2]
    cen = P[mol.ravel()].mean(axis=0)
    head, tailc = P[mol[:, 0]], P[mol[:, 1:]].mean(axis=1)
    u = head - tailc
    u -= e.L * np.round(u / e.L)
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    rel = P[mol[:, 0]] - cen
    rel -= e.L * np.round(rel / e.L)
    r_head = np.linalg.norm(rel, axis=1)
    s = np.einsum("ic,ic->i", u, rel / np.maximum(r_head, 1e-9)[:, None])

    wi = e._wi
    wrel = P[wi] - cen
    wrel -= e.L * np.round(wrel / e.L)
    r_w = np.linalg.norm(wrel, axis=1)
    trel = P[mol[:, 1:].ravel()] - cen
    trel -= e.L * np.round(trel / e.L)
    r_t = np.linalg.norm(trel, axis=1)

    core = np.median(r_t)                       # tail-core radius
    lumen_r = max(core - (nb - 1) * BOND_REST, 0.0)
    lumen_w = int((r_w < lumen_r).sum()) if lumen_r > 0.3 else 0
    lumen_tail = int((r_t < lumen_r).sum()) if lumen_r > 0.3 else 0
    return dict(inner=int((s < 0).sum()), outer=int((s > 0).sum()),
                core=float(core), lumen_r=float(lumen_r),
                lumen_w=lumen_w, lumen_tail=lumen_tail,
                r_head_mean=float(r_head.mean()))


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    sizes = [int(v) for v in (sys.argv[2] if len(sys.argv) > 2 else "50,65,80,100,120").split(",")]
    cv = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    print(f"PLANTED BILAYER RINGS, curvature={cv}, steps={steps}", flush=True)
    print(f"{'N':>5}{'R_mid':>7}{'out/in':>9}{'t':>8}{'inner':>7}{'outer':>7}"
          f"{'core':>7}{'lumen_r':>9}{'lumenW':>8}{'lumenT':>8}   verdict", flush=True)
    for n_lip in sizes:
        nb = 3
        e = build(0, plant=False, n_lip=n_lip, n_water=max(250, 4 * n_lip), **CFG)
        e.curvature = cv
        R_mid, n_out, n_in = plant_ring(e, n_lip, nb)
        p0 = profile(e, n_lip, nb)
        for t in (0, steps):
            if t:
                for _ in range(steps):
                    e.step()
            p = profile(e, n_lip, nb)
            # A lumen must HOLD WATER. Judging it from lumen_r alone reported "HOLLOW" for N=65
            # when the render showed a filled micelle: lumen_r = core - molecular_length is positive
            # for any aggregate whose tail median exceeds the molecule length, filled or not.
            # CONNECTIVITY GATE, added after a second false positive. At N=80 the ring split into
            # two micelles; the centroid then sat BETWEEN them and the metric read the water-filled
            # gap as a lumen of 64 waters. A lumen is only defined for a SINGLE connected aggregate,
            # so anything fragmented is disqualified before the lumen is even considered.
            frac_intact = len(largest_cluster(e)) / n_lip
            hollow = (frac_intact >= 0.9 and p["lumen_w"] >= 5 and p["lumen_r"] > 0.5
                      and p["lumen_tail"] <= 0.05 * n_lip * (nb - 1))
            frac_intact = len(largest_cluster(e)) / n_lip if t else 1.0
            verdict = ("HOLLOW" if hollow and t else
                       "filled" if t and p["lumen_r"] > 0.5 and frac_intact >= 0.9 else
                       f"fragmented {frac_intact:.0%}" if t and frac_intact < 0.9 else
                       "opened/lost" if t else "planted")
            render(e, f"PLANTED RING N={n_lip} curvature={cv} t={t}",
                   f"ring_N{n_lip:03d}_t{t}")
            print(f"{n_lip:>5}{R_mid:>7.2f}{f'{n_out}/{n_in}':>9}{t:>8}"
                  f"{p['inner']:>7}{p['outer']:>7}{p['core']:>7.2f}{p['lumen_r']:>9.2f}"
                  f"{p['lumen_w']:>8}{p['lumen_tail']:>8}   {verdict}", flush=True)
