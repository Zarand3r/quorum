"""Concentration is the standard axis of a surfactant phase diagram -- micelle -> rod -> lamellar is
driven by raising the surfactant fraction, and every run in this project has sat at one dilution.
Shrinking the box consolidated the aggregates (spanning 0.38 -> 0.60 as half-width went 8 -> 5) but
bottoms out: the membrane is ~5 thick, so a box under ~10 wide would let the bilayer feel its own
periodic image. So raise lipid fraction at FIXED box instead.

Original note: the blocker is SIZE, not chemistry. Ribbons stabilise at 15-20 lipids; spanning a box of width 22
needs 44 (22 per leaflet), so they would have to fuse three-fold and end-to-end fusion is slow.

Match the box to the natural ribbon instead: at width 10 a spanning bilayer needs ~20 lipids, which
is what one ribbon already holds. Lipid count is derived from the box (2 per unit width, both
leaflets) and water is scaled to hold the token density of the reference run constant, so the only
variable is box size.

`spanning` is measured directly: the fraction of the periodic axis the largest aggregate covers.
A spanning bilayer must WRAP the box, so this goes to ~1.
"""
import subprocess
import numpy as np
from bicelle2d import build
from harness import bond_stats, largest_cluster, measure, unwrap, _periodic_axes

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
W = 520
DENS = 439 / (22.0 ** 2)          # tokens per unit area in the reference run
BASE = dict(kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0,
            bond_span=2.0, polarity=0.80, head_q=1.2, hydrophobic=0.6)

def spanning_frac(e):
    """Fraction of the periodic x-axis covered by the largest aggregate, via occupancy binning.

    Extent is useless here: an unwrapped aggregate that WRAPS reports a span larger than the box.
    Binning the wrapped x of its beads and counting occupied bins measures coverage instead, which is
    what "spans the box" actually means.
    """
    comp = largest_cluster(e)
    if len(comp) < 3:
        return 0.0
    idx = e._mol[comp].ravel()
    x = np.mod(e.X[idx, 0] + e.cfg.pos_bound, 2 * e.cfg.pos_bound)
    nb = max(8, int(2 * e.cfg.pos_bound))
    return float(len(np.unique((x / (2 * e.cfg.pos_bound) * nb).astype(int))) / nb)

def shoot(e, tag, title, sub):
    B = e.cfg.pos_bound; sc = (W * 0.42) / B; c = W / 2
    P = unwrap(e, np.arange(len(e.X)))[:, :2]; P = P - P[e.species != 0].mean(0)
    sp, sig = e.species, e.sigma
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}">'
         f'<rect width="{W}" height="{W}" fill="#0b0e13"/>']
    for i in np.where(sp == 0)[0]:
        o.append(f'<circle cx="{c+P[i,0]*sc:.1f}" cy="{c-P[i,1]*sc:.1f}" r="{sig[i]*sc:.1f}"'
                 f' fill="#1e3a5f" opacity="0.24"/>')
    nbd = len(e._mol) * (e._mol.shape[1] - 1)
    for a, b in zip(e._bond_i[:nbd], e._bond_j[:nbd]):
        if np.abs(P[b] - P[a]).max() > B: continue
        o.append(f'<line x1="{c+P[a,0]*sc:.1f}" y1="{c-P[a,1]*sc:.1f}" x2="{c+P[b,0]*sc:.1f}"'
                 f' y2="{c-P[b,1]*sc:.1f}" stroke="#e2e8f0" stroke-width="0.9" opacity="0.5"/>')
    for i in np.where(sp != 0)[0]:
        col = "#38bdf8" if int(sp[i]) == 5 else "#fb923c"
        o.append(f'<circle cx="{c+P[i,0]*sc:.1f}" cy="{c-P[i,1]*sc:.1f}" r="{sig[i]*sc:.1f}"'
                 f' fill="{col}" opacity="0.74" stroke="#0b0e13" stroke-width="0.5"/>')
    o.append(f'<rect x="0" y="{W-42}" width="{W}" height="42" fill="#0b0e13" opacity="0.92"/>'
             f'<text x="9" y="{W-25}" fill="#e2e8f0" font-family="monospace" font-size="12">{title}</text>'
             f'<text x="9" y="{W-8}" fill="#94a3b8" font-family="monospace" font-size="11">{sub}</text></svg>')
    fn = f"{OUT}/{tag}"; open(fn + ".svg", "w").write("".join(o))
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cr_{tag}", f"--screenshot={fn}.png",
                    f"--window-size={W+16},{W+16}", f"file://{fn}.svg"], capture_output=True)

print(f"  {'phi_lip':>8}{'n_lip':>7}{'water':>7}{'span':>7}{'clust':>7}{'align':>7}{'pack':>7}  verdict",
      flush=True)
for B, n_lip, n_water in ((11.0, 63, 250), (11.0, 110, 180), (11.0, 160, 100), (11.0, 200, 40)):
    e = build(7, n_lip=n_lip, bound=B, n_water=n_water, plant=False, **BASE)
    for _ in range(20000):
        e.step()
    m = measure(e); mean, _, frac = bond_stats(e); sf = spanning_frac(e)
    phi = 3 * n_lip / (3 * n_lip + n_water)
    print(f"  {phi:>8.2f}{n_lip:>7}{n_water:>7}{sf:>7.2f}{m['cluster_frac']:>7.2f}{m['align']:>7.3f}"
          f"{m['packing']:>7.3f}  {'OK' if m['ok'] else m['why'][:22]}", flush=True)
    shoot(e, f"conc_{n_lip}", f"lipid fraction {phi:.2f} ({n_lip} lipids), dispersed, t=20000",
          f"spanning {sf:.2f}  cluster {m['cluster_frac']:.2f}  align {m['align']:.3f}  "
          f"packing {m['packing']:.3f}  bond {mean:.3f}")
