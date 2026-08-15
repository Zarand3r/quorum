"""Can Vivarium's excluded volume hold beads apart, and does head/tail shape produce curvature?

Two physical questions, both prerequisites to any membrane phase, and both measured on a planted
flat bilayer relaxed under the real force field.

(1) INTERPENETRATION. A planted bilayer relaxes from spacing 1.000 to 0.380 -- beads sit at 38% of
    the nominal contact distance (steric radius 0.5 each). A membrane whose beads are inside each
    other has no defined thickness and no lumen can be held open. The oracle's bounded core has a
    contact energy of 30-100 eps and simply does not allow this; below ~10 eps it collapses, which is
    the same transition. Sweep `repel` and the saturating core `repel_sharp` and ask whether ANY
    setting keeps the median non-bonded separation near contact.

(2) SHAPE. `head_sigma` scales the head's steric radius relative to the tail's, and the engine's own
    comment identifies it as the head-area/tail-volume ratio, i.e. the packing parameter P. It
    defaults to 1.0, so Vivarium's lipid is a uniform CYLINDER with zero intrinsic curvature. In a
    fundamental-force model spontaneous curvature must come from molecular shape, not from an added
    coarse-grained term, so this is the physical knob the oracle's beta was standing in for.

FALSIFICATION  if no (repel, sharp) setting raises nn/contact above ~0.8, Vivarium's excluded volume
               cannot support a membrane and the core must be redesigned rather than retuned.
"""
import sys
import numpy as np
from bicelle2d import build
from fig2d import render
from polar_pack import BOND_REST

BASE = dict(n_lip=40, bound=11.0, kt=0.02, speed=0.001, k_bond=30.0, satt=0.30,
            n_tail=2, bond_span=2.0, n_water=250, polarity=0.80, head_q=1.2,
            hydrophobic=0.6, attract=1.5)


def plant_flat(e):
    mol, nb = e._mol, e._mol.shape[1]
    per = len(mol) // 2
    xs = (np.arange(per) - (per - 1) / 2.0) * BOND_REST
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        for bead in range(nb):
            off = 0.5 + (nb - 1 - bead) * BOND_REST
            e.X[idx[:, bead], 0] = xs[:len(idx)]
            e.X[idx[:, bead], 1] = sgn * off


def metrics(e):
    """median non-bonded separation / nominal contact, and the bilayer thickness."""
    mol, nb = e._mol, e._mol.shape[1]
    P = e.X[:, :e.pd]
    beads = mol.ravel()
    owner = np.repeat(np.arange(len(mol)), nb)
    d = P[beads][:, None, :] - P[beads][None, :, :]
    d -= e.L * np.round(d / e.L)
    r = np.linalg.norm(d, axis=2)
    same = owner[:, None] == owner[None, :]
    r[same] = np.inf
    np.fill_diagonal(r, np.inf)
    contact = 2.0 * float(np.median(e.sigma[beads])) if getattr(e, "sigma", None) is not None \
        else e.repel_contact
    head, tail = P[mol[:, 0]], P[mol[:, 1:]].mean(axis=1)
    up = head[:, 1] > tail[:, 1]
    thick = float(head[up][:, 1].mean() - head[~up][:, 1].mean()) if up.any() and (~up).any() else 0.0
    return float(np.median(r.min(axis=1)) / contact), abs(thick)


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"planted flat bilayer relaxed {steps} steps; contact = 2*sigma")
    print(f"{'repel':>7}{'sharp':>7}{'head_sig':>10}{'nn/contact':>12}{'thickness':>11}   note",
          flush=True)
    for repel, sharp, hs in [(12.0, 0.0, 1.0), (24.0, 0.0, 1.0), (48.0, 0.0, 1.0),
                             (96.0, 0.0, 1.0), (12.0, 2.0, 1.0), (12.0, 8.0, 1.0),
                             (48.0, 8.0, 1.0), (48.0, 8.0, 1.6), (48.0, 8.0, 2.2)]:
        e = build(0, plant=False, repel=repel, sharp=sharp, head_sigma=hs, **BASE)
        e.curvature = 0.0
        plant_flat(e)
        for _ in range(steps):
            e.step()
        nn, th = metrics(e)
        tag = f"ster_r{int(repel)}_s{int(sharp)}_h{int(hs*10)}"
        render(e, f"repel={repel} sharp={sharp} head_sigma={hs} t={steps}", tag)
        note = "holds" if nn > 0.8 else ("partial" if nn > 0.6 else "interpenetrating")
        print(f"{repel:>7.0f}{sharp:>7.1f}{hs:>10.1f}{nn:>12.2f}{th:>11.2f}   {note}", flush=True)
