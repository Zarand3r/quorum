"""Look at the actual positions and orientations, verified against a KNOWN structure first.

Every structural claim in this project has been made from a scalar, and every time an image or a raw
profile was consulted it CONTRADICTED the scalar: a "SLAB" that was a droplet, an "aspect 0.189" that
was a 23-lipid fragment, a "ring" that was a filled blob. This prints the raw geometry so a claim can
be checked directly rather than through a reduction.

It is validated the only honest way: run it on a PLANTED bilayer, where the answer is known by
construction, and confirm the numbers match what was planted. A tool that cannot reproduce a known
structure cannot be trusted on an unknown one.
"""

import numpy as np
from bilayer3d import build
from harness import largest_cluster, measure, unwrap


def dump(e, tag, expect=None):
    mol = e._mol
    comp = largest_cluster(e)
    idx = mol[comp]
    P = unwrap(e, idx.ravel(), ref=idx[0, 0]).reshape(len(comp), idx.shape[1], e.pd)
    heads, tails = P[:, 0], P[:, 1:]

    # ORIENTATION: head -> mean tail, per molecule. Never inspected directly before now.
    u = tails.mean(axis=1) - heads
    u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)

    c = P.reshape(-1, e.pd) - P.reshape(-1, e.pd).mean(0)
    ev, evec = np.linalg.eigh(c.T @ c / len(c))
    normal = evec[:, 0]                       # thin axis
    proj_h = (heads - P.reshape(-1, e.pd).mean(0)) @ normal
    tilt = np.degrees(np.arccos(np.clip(np.abs(u @ normal), 0, 1)))

    m = measure(e)
    print(f"\n  {tag}   n={len(comp)}/{len(mol)}  bond={m['bond_mean']:.2f}  ok={m['ok']}")
    print(f"    head positions along the thin axis: two peaks = bilayer")
    hist, edges = np.histogram(proj_h, bins=12)
    for i, h in enumerate(hist):
        z = 0.5 * (edges[i] + edges[i + 1])
        print(f"      {z:+6.2f}  {'#' * int(30 * h / max(hist.max(), 1))}")
    print(f"    lipid tilt from the membrane normal: {tilt.mean():5.1f} deg "
          f"(0 = upright, 90 = lying flat)")
    up = (u @ normal) > 0
    print(f"    leaflet split: {up.mean():.2f} up / {1 - up.mean():.2f} down "
          f"(0.50/0.50 = two opposed leaflets)")
    if expect:
        for k, (got, want, tol) in expect.items():
            ok = abs(got - want) <= tol
            print(f"    CHECK {k}: got {got:.2f}, expect {want:.2f} +/- {tol}  "
                  f"{'PASS' if ok else 'FAIL'}")


KW = dict(n_lip=231, bound=5.0, kt=0.02, speed=0.002, repel=12.0, k_bond=40.0, satt=0.30,
          spol=0.90, n_tail=4, head_q=0.0, rad_head=0.0, no_water=True, aniso=0.0,
          polarity=0.0, attract=0.30, bond_span=2.0, wall_axes=())

if __name__ == "__main__":
    e = build(seed=0, plant=True, **KW)
    mol, comp = e._mol, largest_cluster(e)
    P = unwrap(e, mol[comp].ravel(), ref=mol[comp][0, 0]).reshape(len(comp), -1, 3)
    u = P[:, 1:].mean(axis=1) - P[:, 0]
    u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)
    c = P.reshape(-1, 3) - P.reshape(-1, 3).mean(0)
    nrm = np.linalg.eigh(c.T @ c / len(c))[1][:, 0]
    tilt = float(np.degrees(np.arccos(np.clip(np.abs(u @ nrm), 0, 1))).mean())
    dump(e, "VALIDATION: planted bilayer (answer known by construction)",
         expect={"tilt (planted lipids are upright, so ~0 deg)": (tilt, 0.0, 15.0)})
