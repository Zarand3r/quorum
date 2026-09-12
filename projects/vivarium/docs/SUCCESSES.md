# Successes — every confirmed emergent vesicle, and exactly how to get it back

**This file exists because the project already lost one.** The original 2-D vesicle is now
unreproducible: its states were overwritten in place by a relaunch
(`states_protected/former_sd45007_*`, whose filename says step 960,000 while the file reports
1,600,000), and it was scored on a gate that has since been tightened. Nobody wrote down the recipe.

So: every confirmed emergence goes here, with the exact command, the exact seed, the exact step, the
measurement, and the picture. **Append on every success. Never edit a past entry** — if something is
later retracted, add a line saying so rather than rewriting it.

A success qualifies for this file only if **all three** hold:

1. `vesicle_call` returns True — dilation ladder `[1,1,1,1]` and lumen ratio ≥ 0.10
2. the state at the moment of passing is **saved to disk**, not just the final frame
3. someone has **looked at the render** and written down what it actually shows

---

## Common setup

All entries use the **production chemistry** — all six affinities, explicit solvent — and a dispersed
random start with **nothing planted**.

```
chi:   TT 0.70   HH 0.20   HT -0.25   HW 0.75   TW 0.00   WW 0.50
kT 0.45   phi 0.55   dt 8e-3   bend_r0 2.0 (the default; NO bending stiffness)
lipid: 4-tail branched, 5 beads          engine: transformer
```

Two facts worth keeping attached to that table:

- **Bending stiffness is not required.** Every entry ran at `bend_r0 = 2.0`, which the F3 analysis
  shows gives *zero* harmonic bending stiffness. Vesicles form anyway.
- **They all close the same way: two ends of a ribbon meeting**, at *constant* aggregate size — never
  by an aggregate curving. Watch `largest` across checkpoints; it does not change through closure.

Interpreter used for every command below:

```bash
cd /home/rbao/quorum/projects/vivarium
RF=/home/rbao/quorum/bazel-bin/projects/vivarium/serve.runfiles
PY=$RF/rules_python~~python~python_3_12_x86_64-unknown-linux-gnu/bin/python3
export PYTHONPATH="$RF/_main/projects/vivarium:\
$RF/rules_python~~pip~vivarium_deps_312_numpy/site-packages:\
$RF/rules_python~~pip~vivarium_deps_312_pyyaml/site-packages"
```

---

## #1 — seed 509, N = 160. The first verified one.

| | |
|---|---|
| config | `N=160, L=65.0, kT=0.45, phi=0.55` (2 959 beads) |
| first passed | **step 500 000** |
| held | **26 checkpoints** (~260 k steps) |
| cluster | **56 of 160** lipids |
| lumen ratio | 0.136 |
| render | **clean closed ring**, water-filled lumen, heads on both faces |
| state | `docs/controls/emergent_vesicle_sd509_s500000.npz` (tracked in git) |
| figure | `docs/figures/emergent_sd509_captured.png` |

```bash
$PY -c "import sys; sys.path.insert(0,'.'); import emerge_reduced as E
print(E.run_one('0', 509, 800_000, 10_000, 160))"
```

**How it formed.** The cluster sat at **56 lipids, constant, for 100 000 steps before closure and
after** — a ribbon wrapping until its two ends met. It later grew to 85 by accretion, which added
appendages and no lumen.

**How it was nearly lost.** The first run saved only the *final* state, and by step 1e6 the vesicle
had decayed back to a branched tangle — so the render showed an artifact and the vesicle itself was
never on disk. The harness now saves at the moment the gate first passes. Re-running seed 509
reproduced closure at the same step exactly.

This one is shipped as the viewer's default (`server.py --vesicle`, `--vesicle-start formed`).

---

## #2 — seed 904, N = 56. Passes the gate; renders as a lasso.

| | |
|---|---|
| config | `N=56, L=38.45` (1 036 beads) — density-matched, H11 |
| first passed | **step 600 000** |
| held | 3 checkpoints |
| cluster | **56 of 56** lipids (the whole system) |
| lumen ratio | 0.196 |
| render | **a closed loop with a substantial tail** — a lasso, not a tidy ring |
| state | `docs/states_emerge/VESICLE_0_N56_sd904_s600000.npz` |
| figure | `docs/figures/h11_N56_sd904.png` |

```bash
$PY emerge_reduced.py --arm 0 --n-lip 56 --match-density --seeds 20 --seed0 900 --check-every 10000
```

**Recorded as a success with a caveat**, because rule 3 above is the point of this file: the numbers
are clean (ratio nearly 2× threshold, stable across all four dilations) and the picture is borderline.
A count of gate passes is not a count of vesicles.

---

## #3 — seed 903, N = 112. The cleanest small one.

| | |
|---|---|
| config | `N=112, L=54.38` (2 071 beads) — density-matched, H11 |
| first passed | **step 850 000** |
| cluster | **35 of 112** lipids |
| lumen ratio | **0.454** — 4.5× threshold, the highest on record |
| render | **clean closed ring**, lumen clearly visible, coexisting with separate open ribbons |
| state | `docs/states_emerge/VESICLE_0_N112_sd903_s850000.npz` |
| figure | `docs/figures/h11_N112.png` |

```bash
$PY emerge_reduced.py --arm 0 --n-lip 112 --match-density --seeds 20 --seed0 900 --check-every 10000
```

**Why this one matters most for the mechanism.** It is **35 lipids out of 112** — a small vesicle that
closed while the rest of the system stayed as unincorporated ribbons. That is the "several small
aggregates, one of which closes" picture directly, and the smallest vesicle observed so far.

---

## #4 — seed 915, N = 112. A clear ring with a tail.

| | |
|---|---|
| config | `N=112, L=54.38` (2 071 beads) — density-matched, H11 |
| first passed | **step 950 000** |
| cluster | **67 of 112** lipids |
| lumen ratio | 0.162 |
| render | **a clear closed ring with a ribbon tail attached** — between #3's clean ring and #2's lasso |
| state | `docs/controls/emergent_vesicle_N112_sd915_s950000.npz` |
| figure | `docs/figures/h11_N112_sd915.png` |

```bash
$PY emerge_reduced.py --arm 0 --n-lip 112 --match-density --seeds 20 --seed0 900 --check-every 10000
```

Same command as #3 — the N = 112 cell produced **two of the twenty**. First passage at step 950 000,
the latest on record, which is a reminder that a 300 k or even 800 k run would have missed it.

---

## What is actually reproducible, stated plainly

**The recipe is: production chemistry, dispersed start, run ~1e6 steps, and check often enough.**
There is no trick beyond that, and no parameter was tuned to produce any of these.

What we do **not** have is control. The rate is roughly 1–2 runs in 20, and
`specs/2026-09-11_H11_density_matched_N.md` tested whether system size moves it. At the time of
writing three of four cells are complete — **N=56 1/20, N=80 0/20, N=112 2/20** — none clearing the
registered bar of 4/20. System size is not the lever.

A pattern worth watching as more arrive: **the cleanest rings are the ones made of a MINORITY of the
system's lipids** (#3 is 35 of 112), while the ones made of nearly everything (#2 is 56 of 56) render
as lassos. That is consistent with the closure mechanism — a short ribbon can reach its own ends —
but it is four data points and is recorded as an observation, not a finding.

Three things that matter for getting one at all, learned the expensive way:

1. **Check every 10 000 steps, not 50 000.** Vesicles are transient. Seed 509 held ~260 k steps but
   others hold far less, and a coarse checkpoint walks straight past them.
2. **Save the state when the gate passes.** Final-frame-only saving lost #1 once and lost the
   historical vesicle permanently.
3. **Run long enough.** First passage was at 500 k, 600 k and 850 k steps. A 300 k-step run would have
   found none of the three.
