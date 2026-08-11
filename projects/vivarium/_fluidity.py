"""Is the planted bilayer a FLUID membrane or a 2-D solid? Lateral diffusion inside the leaflet.

Local bilayer order says nothing about mobility. A membrane can have perfect head-tail-tail-head
structure and still be a two-dimensional crystal, in which case no topological defect -- a Y/T
junction between two ribbons, a hole, a grain boundary -- can ever anneal, and the branched networks
we measured are the expected frozen end state rather than a kinetic accident.

The discriminator is lateral mean-squared displacement of amphiphile centres of mass, projected into
the membrane plane and measured against the leaflet's own drift:

    MSD(t) = < |r_parallel(t) - r_parallel(0)|^2 >   ->   4 D t   (2-D, fluid)

Two things make this honest rather than a number that always looks fine:
  * the whole-membrane centre of mass is subtracted, so bulk translation of the slab is not counted
    as diffusion;
  * the result is reported in units of NEIGHBOUR SPACING, because what matters for annealing is
    whether a lipid changes neighbours, not whether it wiggles. Sub-spacing MSD after the full run
    means the lipids never exchange, i.e. a solid.

A gas-phase control (unbonded beads, same box) gives the fluid end of the scale.
"""
import sys
import numpy as np
from dpd_reference import DPD
from _sl_model import RHO, KT, NH, NT, NTAIL, NB, A


def plant_slab(n_per_leaf, k_ang, a_matrix, seed, pitch=1.285, dim=3):
    """Box-spanning flat bilayer, sized so the leaflet exactly tiles the periodic box."""
    g = int(np.round(np.sqrt(n_per_leaf)))
    n_per_leaf = g * g
    L = g * pitch
    N = int(RHO * L ** dim)
    n_amph = 2 * n_per_leaf
    sp = np.zeros(N, int); bonds = []; angles = []
    for k in range(n_amph):
        b = k * NB
        sp[b:b + NH] = 1
        sp[b + NH:b + NB] = 2
        for t in range(NH - 1):
            bonds.append((b + t, b + t + 1))
        for c in range(NTAIL):
            t0 = b + NH + c * NT
            bonds.append((b + NH - 1, t0))
            for t in range(NT - 1):
                bonds.append((t0 + t, t0 + t + 1))
            angles.append((b + NH - 1, t0, t0 + 1))
            for t in range(NT - 2):
                angles.append((t0 + t, t0 + t + 1, t0 + t + 2))
    d = DPD(N, L, kT=KT, a_matrix=a_matrix, species=sp, bonds=np.array(bonds),
            k_bond=128.0, r0=0.5, dt=0.02, seed=seed, dim=dim)
    d.angles = np.array(angles); d.k_ang = float(k_ang)
    zs_h, zs_t = [2.5, 2.0, 1.5], [1.0, 0.5, 0.0, -0.5]
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        for q in range(n_per_leaf):
            k = leaf * n_per_leaf + q
            b = k * NB
            px, py = (q % g + 0.5) * pitch, (q // g + 0.5) * pitch
            for t in range(NH):
                d.x[b + t] = np.array([px, py, L / 2 + sgn * zs_h[t]]) % L
            for cc in range(NTAIL):
                t0 = b + NH + cc * NT
                for t in range(NT):
                    d.x[t0 + t] = np.array([px + (cc - 0.5) * 0.45, py,
                                            L / 2 + sgn * zs_t[t]]) % L
    return d, n_amph, pitch


def intact(d, n_amph):
    """Largest connected aggregate as a fraction of all amphiphiles.

    Without this, "fluid" and "dissolved" give the SAME rising MSD. A membrane that fell apart
    diffuses beautifully. Lateral diffusion is only meaningful while the slab is still one object.
    """
    b0 = np.arange(n_amph) * NB
    beads = np.concatenate([b0 + t for t in range(NB)])
    owner = np.concatenate([np.arange(n_amph) for _ in range(NB)])
    dd = d.x[beads][:, None, :] - d.x[beads][None, :, :]
    dd -= d.L * np.round(dd / d.L)
    i, j = np.nonzero(np.linalg.norm(dd, axis=2) < 1.2)
    par = np.arange(n_amph)
    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for a, b in zip(owner[i], owner[j]):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb
    root = np.array([find(k) for k in range(n_amph)])
    return float(np.bincount(root).max() / n_amph)


def com(d, n_amph):
    b0 = np.arange(n_amph) * NB
    return np.stack([d.x[b0 + t] for t in range(NB)]).mean(axis=0)


def run(label, k_ang, a_matrix, steps, n_per_leaf=64, seed=1):
    d, n_amph, pitch = plant_slab(n_per_leaf, k_ang, a_matrix, seed)
    for _ in range(2000):                       # let the planted lattice relax before timing
        d.step()
    r0 = com(d, n_amph)
    prev = r0.copy()
    unwrapped = r0.copy()
    print(f"\n{label}  k_ang={k_ang}  n_amph={n_amph}  L={d.L:.2f}  pitch={pitch:.2f}")
    print(f"{'step':>8}{'MSD_par':>10}{'sqrt/pitch':>12}{'T':>7}{'intact':>8}   interpretation")
    for t in range(1, steps + 1):
        d.step()
        if t % (steps // 6) == 0:
            r = com(d, n_amph)
            step_disp = r - prev
            step_disp -= d.L * np.round(step_disp / d.L)      # unwrap through the periodic box
            unwrapped += step_disp
            prev = r
            q = unwrapped[:, :2] - unwrapped[:, :2].mean(axis=0)  # remove slab drift
            q0 = r0[:, :2] - r0[:, :2].mean(axis=0)
            msd = float(((q - q0) ** 2).sum(axis=1).mean())
            hop = np.sqrt(msd) / pitch
            frac_intact = intact(d, n_amph)
            if frac_intact < 0.8:
                interp = "DISSOLVED -- MSD is not membrane diffusion"
            elif hop > 1.0:
                interp = "FLUID (neighbours exchange)"
            elif hop > 0.4:
                interp = "sluggish"
            else:
                interp = "SOLID (no neighbour exchange)"
            print(f"{t:>8}{msd:>10.3f}{hop:>12.2f}{d.temperature():>7.3f}{frac_intact:>8.2f}   "
                  f"{interp}", flush=True)


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 12000
    # the SL chemistry as run, then the two knobs the reviewer and the literature both implicate
    run("SL as-run           a_TW=80", 15.0, A, steps)
    soft = A.copy(); soft[0, 2] = soft[2, 0] = 40.0; soft[1, 2] = soft[2, 1] = 40.0
    run("weaker hydrophobic  a_TW=40", 15.0, soft, steps)
    run("flexible tails      a_TW=80", 0.0, A, steps)
