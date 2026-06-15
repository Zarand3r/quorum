# Elves harness — setup checklist

Prerequisites for a clean unattended **elves** run on this repo. elves itself generates the plan, survival guide, and execution log during the planning conversation; this checklist is only the things that must exist *before* you launch.

Skill source: `eng-skills` plugin from the [`claude-skills`](https://github.com/Zarand3r/claude-skills) marketplace, auto-installed by `.claude/settings.json`. Project context is in `PLAN.md`; the Judge's ungameable promises are in `docs/constitution.md`.

---

## 1. git + gh (required)

elves' review loop runs on GitHub PRs, so the repo needs a pushable remote and an authenticated `gh`.

```bash
git remote -v                 # a remote you can push to
gh auth status                # logged in with repo scope
git push --dry-run            # confirms push access without changing anything
```

Remote: [`Zarand3r/quorum`](https://github.com/Zarand3r/quorum) (the project was renamed from `pelosi` to `quorum`). The local repo wires `origin` to it:

```bash
git remote add origin https://github.com/Zarand3r/quorum.git
git push -u origin main
```

## 2. A verification gate (required)

elves auto-discovers `pytest` / `npm test` / `cargo test` / `go test` / `Makefile` and runs it after every batch. The gate must **exist and pass on a clean checkout**.

The gate exists: `poetry run pytest` runs the unit + integration suite, including `tests/unit/test_invariants.py` which exercises PLAN.md **I8** (no look-ahead in abnormal return) and **I10** (monotonic-in-time scoring) against `quorum.scoring.abnormal_return` on synthetic data.

For batch 1 of the first elves run, expect the agent to:

1. Run `poetry lock && poetry install` once (the lock was regenerated when deps were pruned).
2. Confirm `poetry run pytest -q` exits 0.
3. Build the Slice 0 pipeline per `PLAN.md` §12.1 against the existing scaffolding (`quorum/scoring/`, `quorum/config/`).

For anything with a UI later (the static HTML event-trace report in §12.1 is not interactive, so this is M6 territory at earliest), add Playwright/Cypress so the gate verifies behavior, not just imports.

## 3. Constitution (already present)

`docs/constitution.md` is the anti-gaming layer the **Judge** checks every batch. It is derived from `PLAN.md` §5 invariants — the two files must stay in sync. When a promise changes, change it in both places in the same commit.

## 4. Survive long runs (recommended for multi-hour runs)

If the machine sleeps or the session drops, the run stops.

```bash
tmux new -s elves             # run claude inside this; detach with Ctrl-B then D
# macOS, separately: caffeinate -dimsu
```

Optional: wire a Slack webhook or `ntfy` push for progress while away — see `~/.claude/skills/elves/references/tool-config-examples.md` (or the namespaced plugin path `~/.claude/plugins/.../eng-skills/skills/elves/...` if installed via the team auto-install).

## 5. Decide the run mode

- **Finite** (default): build the plan, then stop. Right for "build Slice 0 to a verified bar."
- **Open-ended**: keep going until you explicitly stop it. Right for "drive the system from Slice 0 toward M5 across nights" — use only after Slice 0 ships.

Set this during planning.

---

## Pre-launch sanity check

```bash
gh auth status                                    # green
git push --dry-run                                # push access
pytest -q                                         # gate (after batch 1 exists)
test -f docs/constitution.md                      # ungameable promises
test -f PLAN.md                                   # scope + invariants source
```

When these all pass, invoke `elves` with `PLAN.md` as the brief, plan the run (~30 min), stage it, then launch and walk away.

---

## Project-specific guidance for the planning phase

When invoking elves to plan the first run, anchor the conversation in:

- **PLAN.md §12.1 Slice 0** is the scope of the first plan. Do not let the plan expand to M1+ in the first run.
- **PLAN.md §5 Invariants I1, I3, I5, I7, I8, I10** are the success criteria for Slice 0 (per §2.1). Every invariant maps to a test in §14.
- **PLAN.md §19 Open Questions** lists decisions that block Slice 0. The planning conversation should either resolve them or explicitly defer them (and note the default).
- **PLAN.md §7 Risks R1–R10** name the cheapest experiments that reduce uncertainty. The batch order should attack the highest-uncertainty risks first.

When the batch order is set, elves freezes it and runs.

## What *not* to ask elves to do on the first run

- Do not run elves to expand the universe to Nasdaq 100. That is M1 and requires Slice 0 to be green first.
- Do not run elves to train the LightGBM event-impact model. That is M5 and requires hundreds of labeled events that do not yet exist.
- Do not run elves with `auto-research` to optimize a metric. There is no signal to optimize until the closed loop produces a dataset.

elves' job in run 1 is to make the loop go round once, end to end, on one ticker. Nothing more.
