# Autonomous roadmap loop — the contract

**Started 2026-09-16 14:00 PDT. HARD DEADLINE 2026-09-17 01:59 PDT (12 h).** Cadence 15 min.

This file is the contract. `LOOP_STATE.tsv` is the append-only tick log. On any wake, read BOTH
before acting. If this file and my memory of the task disagree, **this file wins** — it exists
because a 12-hour loop crosses context compactions and the task drifts otherwise.

## The cycle

Three modes, in order, repeating: **1 → 2 → 3 → 1**.

| mode | what it does | done when |
|---|---|---|
| **1 — implement** | Do the next unblocked roadmap item (§9 of `ROADMAP.md`). Write code, register the spec BEFORE any run, launch the run. | the change is written and any run is launched |
| **2 — review** | Review what mode 1 just did, for **bugs** and for **unnecessary complexity**. Delete what is not needed. Re-run the affected tests. Verify any new instrument SEPARATES its controls. | the review is done and findings are fixed or recorded |
| **3 — document** | Record the result. Update `SUMMARY.md` and `ROADMAP.md` **in the same commit**. Then decide: significant enough to stop and re-assess, or continue to mode 1. | committed |

**Mode 3 is the only mode that may stop the loop.**

## Choosing the mode on each wake

1. **A run is in flight** (check `LOOP_STATE.tsv` for a PID, then `ps -p <PID>`) → stay in the
   current mode, log a tick, do nothing else. Do not start parallel work; this box has 16 physical
   cores and 12-way is the measured throughput optimum.
2. **Otherwise** → advance to the next mode in the cycle and do it.
3. Always append a row to `LOOP_STATE.tsv`, every tick, including no-op ticks.

## Item order — work down this list, skipping blocked items

Taken from `ROADMAP.md` §9. **Item 1 there (the token-channel decision) is SKIPPED: it is
explicitly a judgement call no run can settle, and it needs a person.** Do not attempt it. Do not
make the suite green by weakening `test_mlp_is_live_not_decorative`.

1. **D9 — plant the ribbon at the relaxed spacing** 1.7651 σ, not the hard-coded `gap = 1.05`.
   ~1 h at 12-way. Prerequisite for BF's AC-4.
2. **BF — the angle potential.** Spec already registered: `specs/2026-09-16_chain_bending_form.md`.
   Five acceptance criteria, all fixed before data. Do not edit them now that data is possible.
3. **D1 — long-range head–head repulsion.** Needs its own spec first, and a momentum test plus a
   gradient gate in the first commit (the sister implementation was non-conservative for three
   months undetected).
4. amp 4.0; then the D4/D5 fidelity defects.

## Invariants — these override anything that looks faster

- **NEVER `pkill -f`.** It has matched my own shell repeatedly. Kill by explicit PID. Killing a
  `ProcessPoolExecutor` parent orphans its workers — kill the worker PIDs too.
- **Do not push to origin.** `origin/main` is frozen at `f96c717e`. Commit locally only.
- **Do not tune a parameter to make a gate pass.** Report every value run.
- **Amend a registered gate only BEFORE its data exists**, as a dated amendment that strikes
  through the original rather than deleting it.
- **Criteria before data.** A spec in `specs/` before the run, scored mechanically.
- **R9 — faithful to physics before favourable to the result.** A correct term that makes vesicles
  RARER is a success and is reported as one. BF is pre-registered as expecting exactly that.
- **Validate every new instrument against controls it must SEPARATE**, at the thermal noise of real
  data, including a marginal case. Four metrics died in one day for skipping this.
- **Look at the artifact before believing the statistic.** Render before any structural claim.
- **A test that has never failed is not evidence.** Re-introduce the bug and confirm it trips.

## The box is SHARED — a killed job is not a failed job

Observed 2026-09-16 14:3x: a `bazel test` was killed with "system is running low on memory" while
**other people's work** was running on this machine — a `.venv/bin/python -m pytest tests/ -q` at
2.9 GB RSS and an `oss-cad-suite` Verilog simulator. Neither is ours.

- **Do not kill a process you did not start.** Check `ps -o args -p <PID>` and confirm it is a
  vivarium run before touching it. Ours run from the bazel runfiles python, never from a `.venv`.
- A job killed for memory, or a suite that times out at 900 s, is an **environment** result, not a
  code result. Re-run it when the box is quieter; do not "fix" code in response to it, and do not
  record it as a regression.
- Before blaming a run, check `free -g` and `df -h /tmp` — `/tmp` is RAM-backed tmpfs here, so
  scratch files consume memory. A previous session put 20 GB there and lost five jobs to it.

## Stop conditions — any one of these ends the loop

- **Deadline** 2026-09-17 01:59 PDT. On any wake at or after it: `CronDelete` immediately, write a
  reviewer handoff to `docs/`, summarise, stop. Do not start new work.
- **Genuinely stuck** — two consecutive cycles with no decidable new result.
- **A result significant enough to re-assess the roadmap** (mode 3's judgement). This is a success
  condition, not a failure: stop, hand off, let a person re-plan.
- **An invariant would have to be broken** to make progress.

On stopping: `CronDelete` the job, write `docs/REVIEWER_HANDOFF_<date>.md`, and give a concise
summary — what ran, what the registered gates returned verbatim, what is unresolved.
