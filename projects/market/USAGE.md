# Usage

Concrete how-to. For the *design*, see `PLAN.md`.

## Build

[bazelisk](https://github.com/bazelbuild/bazelisk) is the only required tool — it reads `.bazelversion` and fetches the right bazel. `rules_python` provides a hermetic CPython 3.12 (mirrored from the repo-root `.python-version`); the first `bazel` run downloads it plus the pinned pip wheels.

Deps come from the `market_deps` pip hub in the root `MODULE.bazel`, pinned in `requirements_lock.txt`. To change deps, edit that lock (a standard pinned requirements file) and re-run `bazel test`.

## Tests

All bazel commands work from anywhere — bazel walks up to find `MODULE.bazel`.

```bash
bazel test //projects/market:test_suite                              # full suite (52 tests)
bazel test //projects/market:test_suite --test_arg=-k --test_arg=unit         # unit only
bazel test //projects/market:test_suite --test_arg=-k --test_arg=integration  # integration only
bazel test //projects/market:test_suite --test_arg=-k --test_arg=invariants   # PLAN.md I8 / I10
bazel test //projects/market:test_suite --test_output=all            # see pytest output
```

Tests are hermetic — the conftest mocks the LLM and injects a fake `OPENAI_API_KEY`, so no network or real key is needed.

## Legacy demo

`market.legacy` is the pre-refinement sentiment-vector pipeline. `demo_market_fetch.py` has no bazel target yet; add a `py_binary` (deps `:market`) to run it under the hermetic toolchain. It needs a real `OPENAI_API_KEY` and network (yfinance), so it is not part of `bazel test`.

What it does:
1. Loads `market.config.settings.AppConfig` from environment variables.
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
- **`Import errors`** — the `market/` package is put on `sys.path` by the target's `imports = ["."]`; run tests via `bazel test //projects/market:test_suite` rather than a bare `pytest`.
- **`bazel: command not found`** — install bazelisk: see https://github.com/bazelbuild/bazelisk (it reads `.bazelversion` and fetches the pinned bazel).
