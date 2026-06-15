# quorum

A real-time **news-impact market state estimator**. Ingests news, filings, and other market-relevant text; extracts structured event-impact signals with an LLM; updates latent market-state estimates with filtering; logs predictions before outcomes are known; and joins them to realized returns to build a growing training dataset.

> News is treated as an exogenous measurement or shock. Prices and returns are noisy observations. The system maintains a latent belief state over expected return, sentiment, volatility, correlation, and uncertainty. **The LLM never decides trades.**

## What to read

The repo has one source of truth and a few derivative docs.

- **`PLAN.md`** — full system design: invariants I1–I10, risks R1–R10, architecture, schemas, vertical Slice 0, milestones M1–M6. **Read this first.**
- **`docs/constitution.md`** — the ungameable promises the elves Judge enforces every batch; derived from PLAN.md §5 and must stay in sync.
- **`docs/ELVES_SETUP.md`** — prerequisites checklist for running the autonomous overnight harness on this repo.
- **`CLAUDE.md`** — routing for Claude Code coding sessions through the `eng-skills` plugin (`karpathy-guidelines`, `principal-production-engineer`, `strategic-engineering-planner`, `implementation-plan`, `cpp-systems-internals`, `auto-research`, `elves`).

## Current state

The repo contains:

- `quorum/scoring/` — pure-numpy abnormal-return computation and outcome scoring (PLAN.md §11.4); the I8/I10 invariants are unit-tested against it.
- `quorum/config/` — environment-driven configuration (DuckDB by default per PLAN.md §8).
- `quorum/legacy/` — the pre-refinement 10-dimension sentiment pipeline, preserved for reference. **Not** on the path for Slice 0 or any milestone; do not extend it.
- `tests/` — unit + integration tests including `tests/unit/test_invariants.py` for I8/I10.

Slice 0 (PLAN.md §12.1) is the next thing to build; it is not built yet.

## Install

Requires Python ≥ 3.10 and [Poetry](https://python-poetry.org/).

```bash
poetry lock          # regenerate the lock file after the recent dep prune
poetry install
export OPENAI_API_KEY="..."
```

## Tests

```bash
poetry run pytest                       # all
poetry run pytest tests/unit            # unit only
poetry run pytest tests/integration     # integration only
poetry run pytest tests/unit/test_invariants.py    # PLAN.md I8/I10
```

Coverage is reported in `htmlcov/index.html` when the `--cov-report=html` flag is included (pytest.ini does so by default).

## Legacy demo (pre-refinement)

For reference only — this is the original 10-dimension sentiment pipeline, **not** Slice 0:

```bash
poetry run python demo_market_fetch.py
```

## Disclaimer

This project is for research and educational purposes only. Outputs must not be used as the sole basis for any financial decision.
