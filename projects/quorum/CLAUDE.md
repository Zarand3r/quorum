# quorum — project-specific instructions

This project is a real-time news-impact market state estimator. It is architecturally significant, performance-sensitive, concurrency-heavy, and safety-relevant (financial signals, closed-loop estimation). The repo-wide CLAUDE.md at the workspace root has the skill routing and engineering rules; this file adds the project-specific anchors.

## Project anchors

- **Plan** — `PLAN.md` is the source of truth for scope, invariants (I1–I10), risks (R1–R10), and milestones (Slice 0 → M1–M6). Read it before proposing changes that cross layers.
- **Constitution** — `docs/constitution.md` lists the ungameable promises the elves Judge enforces every batch. Derived from PLAN.md §5; the two must stay in sync.
- **Harness setup** — `docs/ELVES_SETUP.md` is the prerequisites checklist before launching an overnight elves run on this project.
- **Verification gate** — `tests/unit/test_invariants.py` enforces PLAN.md I8 (no look-ahead in abnormal return) and I10 (monotonic-in-time scoring) against `quorum.scoring.abnormal_return`. This is the gate the elves Judge looks for in batch 1.

## Domain-specific reminders

- **The LLM never decides trades.** The LLM extracts evidence; a filter updates beliefs; a predictor estimates impact; a portfolio/risk layer (when it exists) decides whether to act. This separation is constitutional.
- **As-of discipline is non-negotiable.** Every row that influences a prediction carries `as_of_time_utc`. Naive `datetime.now()` is a bug — use `datetime.now(timezone.utc)`. The scoring layer raises `LookAheadError` on tz-naive inputs.
- **No silent fallback.** Failures log typed errors and skip; never substitute neutral defaults (cf. review M1–M5 in the migration commit; the legacy mock-news scraper is gone).
- **Slice 0 only for the first elves run.** Scope is capped at PLAN.md §12.1. No M1+ work, no LightGBM training, no auto-research until the loop has gone round once.

## Working inside this project

```bash
cd projects/quorum
uv sync --extra dev            # install runtime + dev deps (workspace-aware)
uv run pytest -q               # run the gate
uv run pytest tests/unit/test_invariants.py   # just the I8 / I10 anchor
```

`quorum/legacy/` is the pre-refinement 10-dim sentiment pipeline. Preserved for reference; do not extend it. Build new functionality under `quorum/`.
