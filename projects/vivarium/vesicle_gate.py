"""Is it a vesicle? Two clauses, both physical, no free parameters.

    A vesicle is a connected lipid aggregate whose enclosed void is bounded by that
    aggregate arranged as a bilayer.

CLOSED   the largest connected aggregate encloses a void. Measured with the existing, validated
         `n_enclosed`, but fed ONLY that aggregate's beads -- so three micelles arranged in a ring
         cannot pass by jointly surrounding a pocket. That case is not hypothetical: it scored
         0.5997 against a 0.45 curl threshold on 2026-09-12.

BILAYER  of the lipids in that aggregate, some point their head toward the void and some away. One
         number: the fraction pointing inward. A bilayer has both leaflets, so it sits near 0.5. A
         monolayer loop has one, so it sits at 0 or 1. Per-MOLECULE, which is why it survives
         thermal noise -- three distributional attempts on 2026-09-14 did not, because a relaxed
         bilayer and a relaxed monolayer have the same radial spread once kT blurs them.

WHAT THE BILAYER CLAUSE ACTUALLY CONTRIBUTES, measured 2026-09-14 and weaker than it looks. On all
237 saved emergence states, every one of the 24 that enclose has inward fraction 0.368-0.540 -- inside
any reasonable band, and tracking the geometric prediction (a ring of radius R with bilayer thickness
d has inner/(inner+outer) = (R-d/2)/2R, so a SMALL vesicle is legitimately well below 0.5). So the
clause rejects NOTHING on this data: closure alone yields the same set. It would reject a closed
MONOLAYER loop, which is what it is for -- but no such state occurs here, so the clause is carried on
its physics rather than on demonstrated discrimination. Said plainly because the alternative is to
let it look load-bearing when it is not.

WHAT THIS REPLACES. `vesicle_call` needed a lumen-ratio threshold of 0.10, whose own docstring says
it exists to reject "a branched network that happens to enclose one incidental pocket". That is a
SIZE proxy for a STRUCTURAL question. Ask the structural question and the constant is not needed --
a branched network fails because its void is not bounded by a bilayer, not because the void is small.
The dilation ladder is kept, but as what it is: a robustness check on the rasteriser, inside CLOSED.
"""
from __future__ import annotations

import numpy as np

from _lumen_field import n_enclosed
from field import HEAD, WATER


def _aggregates(X, mols, L, cut=1.4, min_lipids=8):
    """Molecule indices of EVERY connected lipid aggregate, largest first.

    Not just the largest. The definition is EXISTENTIAL -- "a connected aggregate whose enclosed void
    is bounded by that aggregate" -- and in this project the vesicle is often NOT the biggest cluster.
    Rendered on 2026-09-14: in the flagship sd509 state the largest aggregate (56 lipids) is an OPEN
    RIBBON enclosing nothing, while a clean ring sits in a smaller, separate cluster. A first version
    of this file took argmax and therefore rejected two of the four confirmed vesicles.

    BEAD-level connectivity at the same `cut` the project's `largest_lipid_cluster` uses -- a lipid
    joins if ANY of its beads is within `cut` of any bead already in. An earlier version clustered
    MOLECULE CENTROIDS at a different cut and disagreed with the recorded sizes (28 against a
    recorded 56 for sd904) -- R8, one implementation per concept, broken in the file that quotes it.
    """
    beads = np.asarray(mols)
    flat = beads.ravel()
    P = np.asarray(X)[flat]
    nb = beads.shape[1]
    lab = -np.ones(len(P), np.int64)
    cur = 0
    for s in range(len(P)):
        if lab[s] >= 0:
            continue
        stack = [s]
        lab[s] = cur
        while stack:
            i = stack.pop()
            d = P - P[i]
            d -= L * np.round(d / L)
            for j in np.where(((d * d).sum(1) < cut * cut) & (lab < 0))[0]:
                lab[j] = cur
                stack.append(int(j))
        cur += 1
    per_mol = lab.reshape(len(beads), nb)[:, 0]
    out = []
    for c in range(cur):
        members = np.where(per_mol == c)[0]
        if len(members) >= min_lipids:
            out.append(members)
    out.sort(key=len, reverse=True)
    return out


def inward_fraction(X, species, mols, L, members):
    """Fraction of the aggregate's lipids whose HEAD points toward the aggregate centre.

    0.5 -> both leaflets present (bilayer). 0 or 1 -> one leaflet (monolayer).
    """
    beads = np.asarray(mols)[members]
    P = np.asarray(X)
    ref = P[beads[:, 0]][:, None, :]
    rel = P[beads] - ref
    rel -= L * np.round(rel / L)
    ctr = (ref[:, 0, :] + rel.mean(axis=1))                      # per-molecule centroid, unwrapped
    hub = ctr.mean(axis=0)                                       # aggregate centre
    sp = np.asarray(species)
    head = np.array([P[b[sp[b] == HEAD][0]] if (sp[b] == HEAD).any() else P[b[0]] for b in beads])
    tail = np.array([P[b[sp[b] != HEAD]].mean(axis=0) for b in beads])
    ht = head - tail
    ht -= L * np.round(ht / L)                                   # head-minus-tail, the lipid's axis
    out = ctr - hub
    out -= L * np.round(out / L)                                 # outward radial direction
    return float((np.einsum("ij,ij->i", ht, out) < 0).mean())    # head points inward


def vesicle(X, species, mols, L, dilations=(1.0, 1.5, 2.0, 2.5, 3.0), bilayer_band=(0.20, 0.80)):
    """(is_vesicle, score, detail). `score` is graded so a sweep can be gated on it.

    score = closure, with the bilayer clause acting as a VETO rather than a factor:

      closure  fraction of the dilation ladder at which ONE connected aggregate encloses EXACTLY one
               void. This is what actually discriminates -- measured 2026-09-14, all 24 enclosing
               states among 237 pass the bilayer clause, so closure alone yields the same set.
      veto     inward fraction outside the band -> score 0. The band is GEOMETRIC, not picked: a ring
               of radius R and bilayer thickness d has inner/(inner+outer) = (R - d/2)/2R, so the
               smallest plausible vesicle here (R~5, d~4) sits at 0.30 and a monolayer at 0 or 1.
               (0.20, 0.80) brackets every real bilayer with margin and excludes one leaflet.

    A binary call, when one is needed, is closure == 1.0 -- unanimity across the ladder, which is the
    only non-arbitrary cut point. Everything else would be a number somebody chose.
    """
    aggs = _aggregates(X, mols, L)
    if not aggs:
        return False, 0.0, {"n_lipids": 0, "closure": 0.0, "inward_fraction": float("nan"),
                            "bilayer": 0.0}
    # Rank by score, but ALWAYS report a measured inward_fraction. A first version defaulted the
    # detail dict to zeros when every aggregate scored 0, and those zeros were then read as evidence
    # that the bilayer clause had REJECTED the state. It had not: arc0.75 actually measures 0.393 and
    # the three-micelle state 0.409 -- both are made of bilayer. Closure alone does the rejecting
    # here. A default that looks like a measurement is worse than no measurement.
    scored = [_score_one(X, species, mols, L, m, dilations, bilayer_band) for m in aggs]
    return max(scored, key=lambda t: (t[1], t[2]["closure"]))


def _score_one(X, species, mols, L, members, dilations, bilayer_band):
    sub = np.asarray(mols)[members]
    keep = np.unique(sub.ravel())
    Xi = np.asarray(X)[keep]
    remap = {int(b): i for i, b in enumerate(keep)}
    sub_local = np.vectorize(remap.get)(sub)
    spi = np.asarray(species)[keep]

    hits = 0
    for b in dilations:
        cnt = n_enclosed(Xi, sub_local, L, bead=b)[0]
        hits += int(cnt == 1)
    closure = hits / len(dilations)

    frac = inward_fraction(X, species, mols, L, members)
    lo, hi = bilayer_band
    passes_veto = lo <= frac <= hi
    score = closure if passes_veto else 0.0
    ok = closure == 1.0 and passes_veto
    return ok, score, {"n_lipids": len(members), "closure": closure,
                       "inward_fraction": round(frac, 3), "bilayer_veto": bool(passes_veto)}


def validate() -> int:
    """The panel this gate must SEPARATE. Run: `python vesicle_gate.py`.

    Positives are REAL relaxed states (the four confirmed vesicles) plus one planted ring; the
    hardest negative is a relaxed three-micelle state that scored 0.5997 against a 0.45 threshold on
    the previous curl metric, and a planted arc0.75 -- open, but nearly closed.

    Known limit, stated rather than hidden: the planted negatives are step-0, not thermally relaxed.
    Every metric that failed on 2026-09-14 failed by being validated on step-0 plants alone. The
    relaxed members here (4 positives + the micelle state) are what carry the result; the planted
    ones are convenience.
    """
    import pathlib
    import numpy as np
    import _mixture
    from gap_closure import PRODUCTION  # noqa: F401  (documents the chemistry these states used)

    rows = []
    for f in sorted(pathlib.Path(__file__).parent.glob("docs/controls/emergent_vesicle_*.npz")):
        z = np.load(f)
        rows.append((f.name[:30], "VESICLE", vesicle(z["X"], z["species"], z["mols"], float(z["L"]))))
    cs = pathlib.Path(__file__).parent / "docs/states_curl/CURL_s2.0_nr0.3335_sd801.npz"
    if cs.exists():
        z = np.load(cs)
        rows.append(("three micelles (relaxed)", "NOT",
                     vesicle(z["X"], z["species"], z["mols"], float(z["L"]))))
    for tag, plant, N, L in (("planted ring", "arc1.0", 56, 100.0),
                             ("planted arc0.75", "arc0.75", 56, 100.0),
                             ("planted flat", "flat", 56, 100.0)):
        nw = int(round(0.55 * L ** 2 / np.pi * 4)) - N * 5
        X, sp, b, mols, _, _ = _mixture.build(0, N, nw, L, 2, plant=plant, branched=True, seed=1)
        mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
        rows.append((tag, "VESICLE" if plant == "arc1.0" else "NOT",
                     vesicle(np.ascontiguousarray(X, dtype=np.float64), sp, mm, L)))

    print(f"  {'case':>32} {'truth':>8} {'ok':>6} {'score':>7} {'closure':>8} {'inward':>7}")
    for tag, truth, (ok, sc, d) in rows:
        print(f"  {tag:>32} {truth:>8} {str(ok):>6} {sc:>7.3f} "
              f"{d['closure']:>8.2f} {d['inward_fraction']:>7.2f}")
    pos = [sc for _, t, (_, sc, _) in rows if t == "VESICLE"]
    neg = [sc for _, t, (_, sc, _) in rows if t == "NOT"]
    ok = bool(pos) and bool(neg) and min(pos) > max(neg)
    print(f"\n  worst positive {min(pos):.3f}   best negative {max(neg):.3f}   "
          f"margin {min(pos) - max(neg):+.3f}")
    print(f"  SEPARATES: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(validate())
