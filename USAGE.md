# Usage

Concrete how-to. For the *design*, see `PLAN.md`.

## Install

```bash
poetry lock                 # regenerate after a dependency prune
poetry install
export OPENAI_API_KEY="..."
```

## Tests

```bash
poetry run pytest                                # full suite
poetry run pytest tests/unit                     # unit only
poetry run pytest tests/integration              # integration only
poetry run pytest tests/unit/test_invariants.py  # PLAN.md I8 / I10
```

Coverage HTML lands in `htmlcov/index.html`.

## Legacy demo

`quorum.legacy` is the pre-refinement sentiment-vector pipeline. The demo runs it end-to-end against the legacy `MarketContextFetcher` + `EmbeddingParser`:

```bash
poetry run python demo_market_fetch.py
```

What it does:
1. Loads `quorum.config.settings.AppConfig` from environment variables.
2. Tests LLM and market-data connectivity.
3. Fetches market data for the configured target symbols (default `SPY, QQQ, IWM, DIA`) via yfinance.
4. Calls the LLM for a market analysis.
5. Extracts the legacy 10-dimension sentiment embedding from that analysis.
6. Prints the most-significant dimensions.

What it does *not* do:
- No news ingestion — the legacy news/economic-indicator paths returned hardcoded mocks before review M3/M4 and were removed; until PLAN.md §19 picks a real source, those paths return empty.
- No persistence — nothing is written to a database.
- No closed loop — predictions are not logged, outcomes are not scored.

The refined Slice 0 pipeline (PLAN.md §12.1) supersedes all of the above and is not yet built.

## Cost

Per legacy demo invocation: ≈ $0.07–0.20 (one analysis call + one extraction call against `gpt-4`). Override with `OPENAI_MODEL=gpt-3.5-turbo` for ≈ 100× cheaper. PLAN.md I4 will require a persisted cost meter before this is wired into a daily cron.

## Troubleshooting

- **`OpenAI API error`** — confirm `OPENAI_API_KEY` is set and the account has credits.
- **`No market data`** — yfinance occasionally fails on outside-hours queries; retry during market hours or stub yfinance in your environment.
- **`Import errors`** — run from the project root (`cd /path/to/quorum && poetry run ...`) so the `quorum/` package resolves.
- **`poetry install` mismatch with lock** — `poetry.lock` was deleted as part of the dependency prune; run `poetry lock` once to regenerate.
