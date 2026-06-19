# market

A real-time **news-impact market state estimator**. Ingests news, filings, and other market-relevant text; extracts structured event-impact signals with an LLM; updates latent market-state estimates with filtering; logs predictions before outcomes are known; and joins them to realized returns to build a growing training dataset.

> News is treated as an exogenous measurement or shock. Prices and returns are noisy observations. The system maintains a latent belief state over expected return, sentiment, volatility, correlation, and uncertainty. **The LLM never decides trades.**

## What to read

- **`PLAN.md`** — full system design: invariants I1–I10, risks R1–R10, architecture, schemas, vertical Slice 0, milestones M1–M6. **Read this first.**
- **`docs/constitution.md`** — the ungameable promises the elves Judge enforces every batch; derived from PLAN.md §5 and must stay in sync.
- **`docs/ELVES_SETUP.md`** — prerequisites checklist for running the autonomous overnight harness on this project.
- **`CLAUDE.md`** (here) and the repo root `CLAUDE.md` — both are loaded by Claude Code; the root has the universal skill routing, this one has the market-specific anchors.

## Current state

- `market/scoring/` — pure-numpy abnormal-return computation and outcome scoring (PLAN.md §11.4); the I8/I10 invariants are unit-tested against it.
- `market/config/` — environment-driven configuration (DuckDB by default per PLAN.md §8).
- `market/legacy/` — the pre-refinement 10-dimension sentiment pipeline, preserved for reference. **Not** on the path for Slice 0 or any milestone; do not extend it.
- `tests/` — 52 tests (unit + integration), including `tests/unit/test_invariants.py` for I8/I10.

Slice 0 (PLAN.md §12.1) is the next thing to build; it is not built yet.

## Install + test

The Python deps live in `pyproject.toml` here; the lock is shared at the workspace root.

From the workspace root:

```bash
uv sync --package market --extra dev   # install market + its dev deps
uv run --package market pytest -q      # run market's tests
```

From this directory:

```bash
uv sync --extra dev
uv run pytest                                    # all
uv run pytest tests/unit                         # unit only
uv run pytest tests/integration                  # integration only
uv run pytest tests/unit/test_invariants.py      # PLAN.md I8 / I10
```

```bash
export OPENAI_API_KEY="..."     # required for any LLM-touching code
```

Coverage HTML lands in `htmlcov/` next to wherever you ran pytest from.

## Legacy demo (pre-refinement)

For reference only — the original 10-dimension sentiment pipeline, **not** Slice 0:

```bash
uv run python demo_market_fetch.py
```

## Disclaimer

This project is for research and educational purposes only. Outputs must not be used as the sole basis for any financial decision.
