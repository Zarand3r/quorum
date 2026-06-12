# News Impact Market State Estimator — Plan

> Project lens: this is a *closed-loop learning system* first, a trading system much later. The deliverable for v0 is a reproducible dataset of (event → extracted impact → predicted return → realized return) tuples, not P&L.

---

## 1. Goal

Build a real-time system that ingests market-relevant text (news, filings, transcripts, macro events), extracts structured event-impact signals with an LLM, updates latent market-state estimates with filtering techniques, logs predictions before outcomes are known, and joins them to realized returns to build a growing training dataset.

News is treated as an exogenous measurement or shock. Prices and returns are noisy observations. The system maintains a latent belief state over expected return, sentiment, volatility, correlation, and uncertainty.

> The LLM extracts evidence. The filter updates beliefs. The predictor estimates impact. The portfolio/risk layer (later) decides whether to act. **The LLM never decides trades.**

---

## 2. Success Metrics

### 2.1 v0 (Vertical Slice — see §13)

- ≥ 20 events ingested end-to-end, every one with a complete trace: raw article → LLM extraction → state update → prediction → scored outcome.
- 100% of predictions reproducible from `(model_version, feature_snapshot_id, state_snapshot_id, event_ids)`.
- 0 silent extraction failures: every LLM failure is logged with a typed error, never replaced by a neutral default.
- Forward run vs backfill replay on the same event window produces byte-identical state snapshots (replay determinism).

### 2.2 v1 (Post-slice expansion)

- Universe ≥ 100 tickers, sustained ingestion for ≥ 90 days.
- Event-impact prediction has **out-of-sample rank IC > 0** on 5d abnormal return (walk-forward, not in-sample).
- Calibration ECE < 0.15 on directional probability.
- Beats a defined baseline (see §12-R7) by a measurable margin after walk-forward CV.

### 2.3 Non-Goals (explicit)

- Live trading. Paper portfolio is a vNext milestone, live is much later.
- Sub-second latency. Cron-driven minute-to-hour cadence is sufficient.
- Full equity universe. Nasdaq 100 is the cap until v1 metrics are met.
- Replacing LLM extraction with a fine-tuned model.
- Intraday correlation regimes. Daily covariance is the target until covariance is shown useful.
- Reinforcement learning, large transformers, simulation-based market modeling.

---

## 3. Constraints

### 3.1 Hard

- **Single machine for v0.** No distributed message bus, no orchestrator, no k8s. One Python process, one DB file.
- **LLM cost budget: $X/day** (decide in §19). Implies caching by `(article_hash, prompt_version)` and skipping duplicates before extraction.
- **Strict timestamp discipline.** Every row that influences a prediction carries `as_of_time_utc`. No feature derived from data unavailable at prediction time. Verified by replay (§7-I7).
- **No silent fallback.** Failure = logged typed error + skipped event, never neutral defaults.

### 3.2 Soft

- Prefer one tool to many: DuckDB > Postgres+Timescale+DuckDB+Polars+... until the single tool actually hurts.
- Prefer scripts before services: `python run.py` on a cron before FastAPI workers, before Kafka.
- Prefer dense arrays/dataframes (numpy/polars/pyarrow) over dict-of-dict in hot loops.

---

## 4. Architecture Decomposition

```text
News / filings / social / macro events
        ↓
[L1] Ingestion (poll/scrape; normalize timestamps; store raw)
        ↓
[L2] Deduplication + entity linking
        ↓
[L3] LLM event extraction → structured impact JSON
        ↓
[L4] State estimation (per-ticker + market/sector belief state)
        ↓
[L5] Risk structure (dynamic covariance / correlation)
        ↓
[L6] Prediction model (event-impact regressor)
        ↓
[L7] Prediction log → outcome scoring → training dataset
        ↓
[L8] Decision layer (alerts → paper portfolio → live, later)
```

Layers are pipeline stages with explicit interfaces (§8). Each stage writes a typed artifact the next stage reads; no stage reads upstream state out-of-band.

---

## 5. Invariants

Each invariant must map to a test, assertion, metric, or alert (§16).

| ID  | Invariant                                                                                                                       | Verification                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| I1  | **As-of discipline.** No feature row at time `t` is derived from a data row with `published_at_utc > t` or `scraped_at_utc > t`. | Replay test: re-run pipeline at `t`, hash output, compare to live run.   |
| I2  | **Single writer per state row.** Only the state estimator writes `ticker_state_snapshots`; only the cov updater writes covariance. | Audit table on writes; foreign-key write-source tagging.                  |
| I3  | **Reproducibility.** Every prediction reconstructs from `(model_version, feature_snapshot_id, state_snapshot_id, event_ids)`.  | Reconstruction test: given snapshot IDs, regenerate predicted value, byte-equal. |
| I4  | **Bounded LLM cost.** Per-event extraction is cached by `(article_hash, prompt_version)`; daily LLM spend ≤ budget.            | Cost meter + alert on threshold.                                          |
| I5  | **Visible failure.** Every extraction/ingestion/filter failure is logged with typed error code; no row silently substituted.   | Failure count metric; zero rows with `state = "default-on-failure"`.      |
| I6  | **PSD covariance.** All covariance snapshots are positive semi-definite after shrinkage and rank-one shocks.                   | Eigenvalue check on every write; reject if `min_eig < 0`.                 |
| I7  | **Replay determinism.** Backfill over `[t0, t1]` and forward run over `[t0, t1]` produce identical state snapshots.            | Periodic CI replay job; diff state tables.                                |
| I8  | **No look-ahead in abnormal return.** `abnormal_return_{i, t+h}` uses only sector returns realized in `(t, t+h]`.               | Unit test on synthetic returns.                                           |
| I9  | **Event dedup is conservative.** A near-duplicate that adds new information is *not* clustered to the prior event.            | Manual eval set: precision and recall on labeled dup pairs.               |
| I10 | **Outcome scoring is monotonic-in-time.** A prediction at `t` is scored only with data from `(t, t+h]`.                         | Outcome scoring test on synthetic series.                                 |

---

## 6. Architecture Options Considered

For each major decision, two or three options. Pick the simplest that meets v0 metrics.

| Decision                  | Options                                                                                     | v0 pick                                                  | Reason                                                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| State / data store        | Postgres+Timescale; DuckDB single file; SQLite                                              | **DuckDB**                                               | Columnar, parquet-friendly, fast aggregations, no daemon, replayable from a single file.                        |
| Message bus               | Kafka/Redpanda; Redis Streams; in-process queue; cron                                       | **Cron + in-process queue**                              | No infra. Move to streams only when latency / multi-process pressure forces it.                                 |
| Sentiment / alpha filter  | EWMA; Kalman; particle filter; neural SSM                                                   | **EWMA only**                                            | Kalman needs `Q, R, A` per ticker — we have no data to fit them yet (§12-R8).                                   |
| Covariance estimator      | EWMA; DCC-GARCH; factor models; PCA shrinkage                                               | **Deferred to milestone M4**                             | Useless without a return universe ≥ 30 tickers and ≥ 60 days of clean data.                                     |
| LLM mode                  | Realtime per-event; batch nightly; hybrid                                                   | **Realtime, cached, with offline reprocessing job**      | Realtime keeps the closed loop closed. Cache + reprocess job allows LLM version upgrades without losing history. |
| Universe                  | NVDA only; Nasdaq 10; Nasdaq 100; all US equities                                            | **NVDA only for slice 0; Nasdaq 100 at milestone M1**    | Most of the work is end-to-end discipline, not breadth.                                                         |
| Dashboard                 | Streamlit; React+FastAPI; HTML report; CLI                                                  | **CLI + static HTML event-trace report**                 | A dashboard is a dependency. v0 needs the loop to work; UI follows.                                             |
| Market data               | Polygon; Alpaca; IEX; yfinance                                                              | **yfinance for slice 0** (decide for v1 in §19)          | Cheapest path to abnormal-return scoring. Swap later behind an interface.                                       |

---

## 7. Risks and Bottlenecks

For each: cheapest experiment that reduces uncertainty, success criterion, fallback.

| ID  | Risk                                                                  | Cheapest experiment                                                              | Success criterion                                              | Fallback                                                                  |
| --- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| R1  | LLM extraction is unreliable on financial text                        | Hand-label 30 events; compare LLM output to labels; measure schema validity rate | Schema-valid ≥ 95%; direction agrees ≥ 70%                     | Tighter schema, few-shot examples, evidence-quote requirement, retries.   |
| R2  | Timestamp leakage (using future data at "prediction time")            | Replay test (I7) on slice 0                                                      | Forward and replay diff = ∅                                    | Add `as_of_time_utc` audit on every feature column; fail closed.          |
| R3  | Abnormal-return computation has subtle bugs                           | Unit test on a synthetic price series with known sector return                   | Test passes for {flat, trending, jumpy} sectors                | Numerical regression suite; cross-check against a notebook calc.          |
| R4  | LLM cost explodes                                                     | Run extraction on 1 day of news; measure $/event                                 | Daily cost projects below budget                               | Cache by `article_hash`; drop sources before extraction in dedup pass.    |
| R5  | Dedup is too aggressive (drops new info) or too lax (over-counts)     | Build a labeled dup set (50 pairs); tune thresholds                              | Precision ≥ 0.9, recall ≥ 0.8                                  | Manual review queue for the boundary band.                                |
| R6  | Covariance matrix loses PSD                                           | Eigenvalue assertion on every write (I6)                                         | 0 PSD violations over a 90-day backtest                        | Project to nearest PSD matrix; or fall back to diagonal cov for the day.  |
| R7  | No signal — model fails to beat baseline                              | Define baseline up front: sector momentum + LLM direction with EWMA              | Held-out rank IC > baseline by ≥ 0.02                          | Drop universe to where signal is clearest; investigate event types separately. |
| R8  | Filter hyperparams (`Q`, `R`, `A`) can't be tuned without data        | Defer Kalman to M3 (after slice 0 + universe expansion produce ≥ 200 events)    | Slice 0 works with EWMA alone                                  | Stay on EWMA. Reassess at M3.                                             |
| R9  | LLM version drift breaks the dataset                                  | Stamp every extraction with `llm_model_version` + `prompt_version`              | Reprocess job re-extracts cleanly                              | Pin LLM version; rerun on version bumps; keep both rows.                  |
| R10 | Universe entity linking fails on tickers with ambiguous names         | Hand-curate alias map for Nasdaq 100 before any extraction                       | ≥ 98% link accuracy on a held-out set of mentions              | Reject ambiguous mentions with `linkage_confidence < threshold`.          |

---

## 8. Core Entities and Interfaces

DuckDB schemas (v0). Promote to Postgres+Timescale only when concurrency or row counts force it.

### 8.1 `raw_articles`

```sql
CREATE TABLE raw_articles (
    article_id        UUID PRIMARY KEY,
    source            TEXT NOT NULL,
    url               TEXT,
    headline          TEXT,
    body              TEXT,
    published_at_utc  TIMESTAMP NOT NULL,
    scraped_at_utc    TIMESTAMP NOT NULL,
    article_hash      TEXT NOT NULL UNIQUE,  -- sha256(url + headline + body) for LLM cache key
    raw_payload       JSON
);
```

### 8.2 `events`

```sql
CREATE TABLE events (
    event_id            UUID PRIMARY KEY,
    article_id          UUID REFERENCES raw_articles(article_id),
    event_cluster_id    UUID,                 -- shared across duplicates
    event_type          TEXT,
    timestamp_utc       TIMESTAMP NOT NULL,
    source              TEXT,
    headline            TEXT,
    summary             TEXT,
    embedding           DOUBLE[],
    llm_model_version   TEXT,
    prompt_version      TEXT,
    extraction_payload  JSON,
    extraction_status   TEXT NOT NULL          -- 'ok' | 'schema_invalid' | 'llm_error' | 'skipped_dup'
);
```

### 8.3 `event_ticker_impacts`

```sql
CREATE TABLE event_ticker_impacts (
    impact_id     UUID PRIMARY KEY,
    event_id      UUID REFERENCES events(event_id),
    ticker        TEXT NOT NULL,
    relationship  TEXT,            -- 'direct' | 'indirect'
    direction     INT,             -- -1, 0, +1
    magnitude     DOUBLE,
    confidence    DOUBLE,
    novelty       DOUBLE,
    surprise      DOUBLE,
    horizon_days  INT,
    mechanism     TEXT,
    evidence      JSON              -- list of {claim, quote}
);
```

### 8.4 `market_bars`

```sql
CREATE TABLE market_bars (
    ticker         TEXT NOT NULL,
    timestamp_utc  TIMESTAMP NOT NULL,
    open           DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
    volume         DOUBLE, vwap DOUBLE,
    PRIMARY KEY (ticker, timestamp_utc)
);
```

### 8.5 `ticker_state_snapshots`

```sql
CREATE TABLE ticker_state_snapshots (
    snapshot_id                       UUID PRIMARY KEY,
    ticker                            TEXT NOT NULL,
    timestamp_utc                     TIMESTAMP NOT NULL,
    sentiment_fast                    DOUBLE,
    sentiment_slow                    DOUBLE,
    alpha_estimate                    DOUBLE,
    alpha_uncertainty                 DOUBLE,
    volatility_estimate               DOUBLE,
    news_intensity                    DOUBLE,
    novelty_weighted_news_intensity   DOUBLE,
    method_version                    TEXT NOT NULL,
    triggering_event_id               UUID         -- which event produced this update (audit)
);
```

### 8.6 `covariance_snapshots` *(deferred to M4)*

```sql
CREATE TABLE covariance_snapshots (
    snapshot_id        UUID PRIMARY KEY,
    timestamp_utc      TIMESTAMP NOT NULL,
    universe           TEXT NOT NULL,
    method             TEXT NOT NULL,
    half_life_days     DOUBLE,
    tickers            TEXT[],
    covariance_matrix  DOUBLE[][],
    correlation_matrix DOUBLE[][]
);
```

### 8.7 `predictions`

```sql
CREATE TABLE predictions (
    prediction_id            UUID PRIMARY KEY,
    timestamp_utc            TIMESTAMP NOT NULL,
    model_version            TEXT NOT NULL,
    ticker                   TEXT NOT NULL,
    horizon_days             INT NOT NULL,
    predicted_excess_return  DOUBLE,
    predicted_vol_change     DOUBLE,
    predicted_corr_change    DOUBLE,
    confidence               DOUBLE,
    feature_snapshot_id      UUID,
    state_snapshot_id        UUID,
    event_id                 UUID
);
```

### 8.8 `outcomes`

```sql
CREATE TABLE outcomes (
    outcome_id              UUID PRIMARY KEY,
    prediction_id           UUID REFERENCES predictions(prediction_id),
    scored_at_utc           TIMESTAMP NOT NULL,
    realized_excess_return  DOUBLE,
    realized_vol_change     DOUBLE,
    realized_corr_change    DOUBLE,
    prediction_error        DOUBLE,
    hit                     BOOLEAN
);
```

### 8.9 `extraction_failures`

```sql
CREATE TABLE extraction_failures (
    failure_id      UUID PRIMARY KEY,
    article_id      UUID REFERENCES raw_articles(article_id),
    occurred_at_utc TIMESTAMP NOT NULL,
    error_code      TEXT NOT NULL,   -- 'schema_invalid' | 'llm_timeout' | 'rate_limit' | ...
    error_detail    TEXT,
    prompt_version  TEXT,
    llm_model_version TEXT
);
```

---

## 9. Data Flow / Control Flow

### 9.1 Hot path — per-article processing

```python
def process_article(article: RawArticle) -> ProcessResult:
    if article.article_hash in seen_hashes:
        return ProcessResult.SKIPPED_DUP_HASH

    cluster_id = dedup.assign_cluster(article)         # embedding + ticker + time window
    if cluster_id != article.id and not adds_new_info(article, cluster_id):
        return ProcessResult.SKIPPED_DUP_CLUSTER

    extraction = llm.extract(article, prompt_version=PROMPT_VERSION)
    if not extraction.ok:
        failures.log(article, extraction.error)         # I5: visible failure
        return ProcessResult.EXTRACTION_FAILED

    event_id = events.write(article, extraction)
    impacts = events.write_impacts(event_id, extraction.impacts)

    for impact in impacts:
        prior = state_store.latest(impact.ticker)       # I2: single writer enforced here
        shock = compute_news_shock(impact, article.source_reliability)
        updated = state_filter.update_with_news(prior, shock, event_type=extraction.event_type)
        state_store.write(updated, triggering_event_id=event_id)

        feature_snap = features.build(event_id, impact, updated)
        pred = impact_model.predict(feature_snap)
        predictions.write(pred, feature_snap.id, updated.id, event_id)   # I3: snapshot-linked

    return ProcessResult.OK
```

### 9.2 Cold path — daily

```python
def close_loop(date: date):
    returns = market_data.returns_for(date)        # uses only data with as_of ≤ EOD
    # M4+ only:
    # covariance_updater.update(returns)

    for pred in predictions.due_for_scoring(date):
        outcome = score(pred, returns)              # I8, I10
        outcomes.write(outcome)

    calibration_report = evaluate_recent(window_days=30)
    monitoring.write(calibration_report)
```

---

## 10. State Machines / Lifecycles

### 10.1 Article → event → impact

```text
raw_articles.row
   ├── deduped (cluster_id assigned)        → no event row
   └── new event:
         ├── extraction_status = 'ok'        → events.row + event_ticker_impacts.rows
         ├── extraction_status = 'schema_invalid' → events.row + extraction_failures.row
         ├── extraction_status = 'llm_error'      → no events.row, extraction_failures.row only
         └── extraction_status = 'skipped_dup'    → no events.row
```

### 10.2 Prediction lifecycle

```text
predictions.row (at t)
   └── awaiting_scoring (t < scoring_due)
         └── scored (scoring_due ≤ now): outcomes.row written, prediction.scored_at = now
```

### 10.3 Model version lifecycle

Every model artifact has an immutable `model_version`. Reprocessing under a new LLM version produces new `events.row`s with the new `llm_model_version`; old rows are preserved. The dataset materializer joins outcomes to *the most recent* extraction for each `article_id` when training, but keeps all rows for audit.

---

## 11. Modeling Reference

Compact reference; specific equations and tuning ranges live here so §13–§14 can stay short.

### 11.1 Exponential smoothing (slice 0)

```text
α  = 1 - exp(-Δt / τ)
state_t = α * obs_t + (1 - α) * state_{t-1}
```

Half-life per event type:

| Event Type       | τ (half-life) |
| ---------------- | ------------: |
| Breaking news    |       1–3 d   |
| Product news     |       5–20 d  |
| Earnings call    |      20–60 d  |
| Macro news       |       5–20 d  |
| Legal/regulatory |     60–180 d  |

### 11.2 Kalman-style alpha filter (M3+)

```text
x_t  = A x_{t-1} + B u_t + w_t        (state transition)
r_t  = H x_t + v_t                     (observation: abnormal return)

# prediction:
x_pred = A x_prev + B u_t
P_pred = A P_prev Aᵀ + Q
# correction:
S = H P_pred Hᵀ + R
K = P_pred Hᵀ S⁻¹
x_new = x_pred + K (r_t - H x_pred)
P_new = (I - K H) P_pred
```

Symbols: `x`=latent alpha; `u`=news shock; `Q`=process noise; `R`=observation noise; `K`=Kalman gain.

**Do not start here.** Without ≥ 200 ground-truth `(shock, abnormal_return)` pairs we cannot fit `A, B, Q, R`; EWMA is the v0 filter.

### 11.3 EWMA covariance + shrinkage (M4+)

```text
Σ_t = λ Σ_{t-1} + (1 - λ) r_t r_tᵀ
C_ij = Σ_ij / sqrt(Σ_ii Σ_jj)
Σ_shrunk = ρ F + (1 - ρ) Σ_empirical
```

`F` candidates: diagonal, single-factor (market), sector-factor, PCA-factor, identity-scaled. Start with diagonal or sector-factor shrinkage.

Multi-half-life blend:

```text
Σ_blend = w_fast Σ_fast(τ=5–20 d) + w_med Σ_med(τ=60 d) + w_slow Σ_slow(τ=252 d)
```

**News-driven correlation shocks (use carefully):**

```text
Σ_t ← Σ_t + γ z zᵀ
```

Apply only when the result remains PSD (I6); reject otherwise.

### 11.4 Event-impact prediction model (M5+)

Start with LightGBM/XGBoost. Inputs: event_type, ticker, sector, LLM direction/magnitude/confidence/novelty/surprise, source reliability, recent momentum, recent volatility, market regime, sector momentum, correlation-cluster features, current sentiment state, current alpha estimate + uncertainty.

Outputs: predicted 1d, 5d, 20d abnormal return; predicted vol change; predicted correlation change.

Targets (no look-ahead, I8):

```text
abnormal_return_{i, t+h} = return_{i, t+h} - sector_return_{i, t+h}
```

### 11.5 Deferred (vNext or later)

Temporal convolution, GRU/LSTM, temporal fusion transformer, small causal transformer, graph NN over stocks, neural state-space, particle filter, RL.

---

## 12. Vertical Slice Strategy

> Build one end-to-end thread before adding breadth. The slice exercises every layer; the milestones (§13) expand each layer once the slice works.

### 12.1 Slice 0 — *"one ticker, one source, one filter, end-to-end"*

- **Universe:** NVDA only.
- **Source:** one feed (e.g., a curated press-release RSS, or one news API key — pick in §19).
- **Market data:** yfinance daily bars for NVDA + QQQ (sector benchmark).
- **Storage:** one DuckDB file at `data/pelosi.duckdb`. Schemas per §8.
- **LLM extraction:** structured JSON per §8.3, with schema validation; cached by `article_hash + prompt_version`.
- **Dedup:** URL + headline normalization only (no embedding yet).
- **Entity linking:** hard-coded `{"NVDA": ["nvidia", "nvda"]}`. Reject mentions that don't match.
- **Filter:** EWMA sentiment + EWMA abnormal-return baseline. No Kalman.
- **Prediction:** 5d abnormal return vs QQQ, point estimate + confidence proxy = current state uncertainty.
- **Scoring:** after 5 trading days, compute realized abnormal return, write `outcomes.row`.
- **Runtime:** `python -m pelosi.run` invoked from cron every 15 min. Single process, in-process queue.
- **Output:** CLI summary + static HTML "event trace" report per event (article → extraction → state → prediction → outcome).

### 12.2 What slice 0 proves

- I1, I3, I5, I7, I8, I10 (the discipline invariants).
- The schemas are sufficient.
- LLM extraction is stable enough on a real source (R1).
- Abnormal-return math is correct (R3).
- The replay path matches the forward path (R2).
- Cost per event is within budget (R4).

### 12.3 What slice 0 defers

- Full Nasdaq 100 universe (M1).
- Embedding-based dedup, multi-source (M2).
- Kalman alpha filter (M3).
- Covariance matrix and shrinkage (M4).
- Trained LightGBM model — the v0 "prediction" is rule-based: `predicted_excess_return = magnitude * direction * confidence * f(novelty)` (M5).
- Paper portfolio, alerts, dashboard (M6).

---

## 13. Milestone Roadmap (post slice 0)

Each milestone: goal, deliverable, scope, non-goals, dependencies, verification, done-when.

### M1 — Universe to Nasdaq 100

- **Goal:** sustain ingestion + extraction + state updates over the Nasdaq 100.
- **Deliverable:** entity-link table for N100; configurable universe; backfill script.
- **Non-goals:** new event types, new sources.
- **Risks addressed:** R10.
- **Verification:** entity-link accuracy on held-out set ≥ 98% (I9); 5 days of live ingestion with < 1% extraction failures.
- **Done when:** N100 sustained for 7 days, slice-0 metrics still green.

### M2 — Second source + embedding dedup

- **Goal:** prevent over-counting when multiple sources cover the same event.
- **Deliverable:** embedding-based clustering; "adds new info" check; labeled dup eval set (50 pairs).
- **Verification:** dedup precision ≥ 0.9, recall ≥ 0.8 (R5).
- **Done when:** dup rate ≤ 1.05× single-source baseline over a week.

### M3 — Kalman alpha filter

- **Goal:** replace EWMA alpha with a Kalman filter once we can fit `A, Q, R` from data.
- **Pre-req:** ≥ 200 logged `(news_shock, abnormal_return)` pairs.
- **Deliverable:** filter implementation; per-event-type parameter fits; A/B against EWMA on backtest.
- **Verification:** Kalman rank IC ≥ EWMA rank IC on held-out; uncertainty `P` is calibrated against squared error.
- **Done when:** A/B win or break-even at lower variance → switch; else keep EWMA, document.

### M4 — Dynamic covariance + shrinkage

- **Goal:** maintain a stable PSD covariance matrix over the universe.
- **Deliverable:** EWMA covariance, multi-half-life blend, sector-factor shrinkage, PSD assertion (I6).
- **Verification:** 0 PSD violations over 90-day replay; sector clusters visible in heatmap.
- **Done when:** covariance available as a feature input and is numerically stable.

### M5 — Trained event-impact model

- **Goal:** beat the rule-based predictor with a supervised LightGBM model.
- **Pre-req:** ≥ a few hundred labeled event/outcome pairs; covariance features available.
- **Deliverable:** feature builder, walk-forward training script, calibration report.
- **Verification:** held-out rank IC > rule-based baseline by ≥ 0.02; calibration ECE < 0.15.
- **Done when:** model promoted via `model_version` bump, both versions retained in `predictions`.

### M6 — Paper portfolio + alerts

- **Goal:** see how predictions would behave in a position-sizing policy.
- **Deliverable:** paper-portfolio engine with `position ∝ alpha / variance`; constraints (max name, max sector, gross, turnover, liquidity, correlation cap); alert rules.
- **Non-goals:** live trading; intraday execution.
- **Verification:** all paper decisions reproducible from inputs; cost/slippage modeled; performance by regime visible.
- **Done when:** 30 days of paper P&L with stable risk exposures.

Beyond M6: temporal/graph/neural state-space models, second-order entity propagation (TSMC → NVDA / AMD / AVGO / ASML), intraday loop, alt-data, live trading. All deferred.

---

## 14. Verification Strategy

Per-invariant tests live alongside code; per-milestone gates block promotion.

**Unit / property tests (always)**
- I8 abnormal-return correctness on synthetic prices.
- I10 outcome-scoring monotonicity.
- I6 PSD eigenvalue check on every covariance write.
- Schema validation on every LLM extraction (I5).

**Replay test (CI, weekly)**
- I7 forward vs backfill diff = ∅ on a frozen 7-day event window.

**Manual eval sets**
- 30 hand-labeled events for extraction quality (R1).
- 50 hand-labeled dup pairs (R5, I9).
- Held-out alias set for entity linking (R10).

**Backtest discipline (M5+)**
- Walk-forward only; no global shuffles; sector-neutral splits where possible.
- Cost-adjusted P&L in paper portfolio (M6); pre-cost is reported only as diagnostic.

**Cost meter (always)**
- Daily LLM spend tracked; alert at 80% of budget (I4).

---

## 15. Implementation Standards

These are tightenings of the invariants for daily implementation work.

- **Timestamp discipline (I1, I8, I10).** Every row that influences a prediction carries `as_of_time_utc`. Never use data unavailable at prediction time.
- **Reproducibility (I3).** Every prediction reconstructs from `(model_version, prompt_version, feature_snapshot_id, state_snapshot_id, event_ids, market_data_version)`.
- **No silent fallback (I5).** Failures log a typed error and skip; never substitute neutral defaults. Default neutral states must be marked explicitly.
- **Audit trail.** For every prediction: article → extracted claims with evidence quotes → impact fields → features → prediction. Static HTML "event trace" report per event in v0.
- **Single writer per state row (I2).** Enforced by code review and write-source tags in the row.
- **Bounded resources (I4).** LLM cost capped, queue sizes capped, retry budgets capped — never unbounded.

---

## 16. Known Failure Modes

| Failure Mode                   | Mitigation                                                                  |
| ------------------------------ | --------------------------------------------------------------------------- |
| Look-ahead bias                | I1 + I7 + I8 + as-of join discipline.                                       |
| Duplicate news overcounting    | Embedding-based clustering (M2) + I9 conservative-dedup rule.               |
| Generic sentiment weakness     | Extract direction, magnitude, novelty, surprise, mechanism — not "sentiment". |
| LLM hallucination              | Schema validation + required evidence spans + retries with typed errors.    |
| Illiquid-stock fake alpha      | Universe capped to Nasdaq 100 until v1.                                     |
| Overfitting                    | Walk-forward CV (M5); paper trading before live (M6).                       |
| Covariance instability         | Shrinkage + multi-half-life blend + PSD assertion (I6).                     |
| Regime overfit                 | Performance reported by regime and year, not aggregated.                    |
| Trading too aggressively       | `position ∝ alpha / variance`; uncertainty-aware sizing (M6).               |
| Poor source quality            | Source reliability weight in news shock; per-source calibration tracking.   |
| LLM version drift              | `llm_model_version` + `prompt_version` stamped; reprocess job (R9).         |

---

## 17. Recommended Next Step

Implement **slice 0** (§12.1):

1. Decide the open questions in §19 that block coding (data source, LLM provider, dedup window, cost budget).
2. Set up the DuckDB schemas from §8 (raw_articles, events, event_ticker_impacts, market_bars, ticker_state_snapshots, predictions, outcomes, extraction_failures).
3. Build the hot path (§9.1) end-to-end for NVDA only with EWMA filter and a rule-based predictor.
4. Build the cold path (§9.2) for daily outcome scoring.
5. Add the unit tests for I8 and I10, and a manual replay diff for I7.
6. Run for one week. Generate the event-trace HTML report. Review.

Stop and review before starting any of M1–M6.

---

## 18. Deferred Complexity

Explicit list of things *not* in v0, *not* in slice 0, and the milestone that re-evaluates them:

| Item                                            | Re-evaluate at      |
| ----------------------------------------------- | ------------------- |
| Full Nasdaq 100 universe                        | M1                  |
| Multi-source ingestion + embedding dedup        | M2                  |
| Kalman filter, Q/R/A fitting                    | M3                  |
| Covariance / correlation matrix                 | M4                  |
| News-driven covariance rank-one shocks          | M4 (cautious, I6)   |
| LightGBM/XGBoost trained model                  | M5                  |
| Walk-forward backtest harness                   | M5                  |
| Paper portfolio + position sizing               | M6                  |
| Alerts + dashboard (Streamlit / React+FastAPI)  | M6                  |
| Kafka / Redpanda / Redis Streams                | When latency forces |
| Postgres + TimescaleDB                          | When DuckDB hurts   |
| FastAPI / Pydantic service                      | When CLI hurts      |
| Polars / pyarrow optimization                   | When numpy hurts    |
| Temporal / graph / neural state-space models    | Beyond M6           |
| Second-order entity graph (supplier/customer)   | Beyond M6           |
| Intraday loop, alternative data, social feeds   | Beyond M6           |
| Reinforcement learning, live trading            | Indefinite          |

---

## 19. Open Questions / Decision Points

Block slice 0 until answered:

1. **News source for slice 0.** Polygon news API? Benzinga? Curated RSS (Reuters / WSJ / company IR pages)? Constraint: timestamped, programmable, affordable.
2. **LLM provider + model.** Claude (Haiku for cost? Sonnet for quality?) vs GPT-4o-mini vs local model. Constraint: structured JSON, evidence spans.
3. **Embedding model** (needed at M2): voyage-3, OpenAI text-embedding-3-small, local BGE? Constraint: cost, quality on financial text.
4. **Market data provider for v1.** yfinance is fine for slice 0; for v1 we likely need Polygon or Alpaca for reliable timestamps + intraday.
5. **LLM cost budget.** $/day cap drives caching and dedup aggressiveness.
6. **Dedup time window.** Fixed (2 h) or event-type dependent? Drives R5 design.
7. **Source reliability scoring.** Hand-curated table or learned over time?
8. **Where does "novelty" / "surprise" ground truth come from?** Self-consistency check against recent extractions, or LLM judgment only?
9. **Prediction confidence semantics.** Calibrated probability, or a state-uncertainty proxy? Affects calibration metric definition.
10. **Replay scope.** Do we replay LLM calls (uses cache → exact) or re-execute (uses live API → may drift)? Affects I7 strictness.

Defer to milestones, but worth noting now:

11. **When does Postgres+Timescale earn its keep over DuckDB?** Concrete row-count / concurrency trigger.
12. **Multi-process writes to state.** Lock strategy when ingestion outgrows one process.
13. **Backfill vs realtime feature parity.** How do we keep the two code paths identical (single implementation, dual schedulers)?
