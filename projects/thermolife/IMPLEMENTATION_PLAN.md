# thermolife — Implementation Plan (Slice 0 + Web Control)

> Turns the locked design in [`PLAN.md`](PLAN.md) into an executable, checklist-first build sequence. **Scope: PLAN.md Slice 0 (§15) — the physical substrate with a hand-coded forager — plus a Tailscale-hosted web endpoint to start / pause / restart / watch the simulation.** Everything learned (the NCA rule, interfaces, plasticity, prediction, TBPTT, curriculum, evolution, particles, torch, GPU) is **out of scope** here — see §C. That deferral *is* the "avoid unnecessary complexity" instruction made concrete.

## Pre-flight (Phase 1)

- **Build, not migrate.** thermolife is design-only: `PLAN.md`, `configs/*.yaml`, `BUILD.bazel`, and docstring-stub `__init__.py` files. There is no code to migrate. This is a from-scratch build sequence.
- **Already aligned (do not rebuild):** `PLAN.md` (design source of truth), `configs/world.yaml` / `model.yaml` / `curriculum.yaml` (declarative constants), `BUILD.bazel` (configs filegroup + skeleton `py_library`), the `env/ model/ train/ eval/ viz/` package dirs.
- **Violates doctrine:** nothing yet — greenfield.
- **New package not in PLAN.md §11:** `sim/` holds the *operational* Slice-0 loop, control state machine, and web server (distinct from `train/`, which is the future TBPTT *training* loop). This plan extends §11 with `sim/`; update PLAN.md §11 when Step 6 lands.
- **Dependencies stay tiny:** `numpy` + `pyyaml` runtime, `pytest` dev. **No torch, no matplotlib, no web framework** — the server is stdlib `http.server`; the viewer is a client-side `<canvas>` fed JSON. torch enters only at M2 (out of scope).

---

## The steps at a glance

- [ ] **Step 0 — Foundation.** `thermolife_deps` pip hub (numpy/pyyaml/pytest), `py_test` target, config loader, one green test. *Test infra only.*
- [ ] **Step 1 — World contract.** `World` SoA (fields + cell channels), config-driven construction, seeded RNG. Locks the data contract.
- [ ] **Step 2 — Field physics.** `diffuse_and_decay`: vectorized stencil diffusion + decay + source injection for nutrient/waste/heat/pheromone.
- [ ] **Step 3 — Transactions + energy.** `apply_conservative_transactions` + `TransactionLedger`: uptake (lossy), cost debits, waste/heat emission. **The conservation core.**
- [ ] **Step 4 — Lifecycle.** Death, one-time decomposition, dead-cell inertness.
- [ ] **Step 5 — Forager + tick loop + Slice-0 gate.** Hand-coded gradient-climbing forager, full `tick()`, headless runner; the "survives on gradient, dies when it's removed" gate + replay determinism.
- [ ] **Step 6 — Web control endpoint (Tailscale).** stdlib `http.server` with a background sim thread + control state machine (start/pause/restart/stop), `/state` JSON, a `<canvas>` viewer, `py_binary`, and `tailscale serve` docs.

**Dependency graph** (near-linear — physics layers stack; the web layer sits on the runnable loop):

```
0 ──▶ 1 ──▶ 2 ──▶ 3 ──▶ 4 ──▶ 5 ──▶ 6
                                   └─ viewer.html (independent, lands with 6)
```

Critical path is the whole chain: `0 → 1 → 2 → 3 → 4 → 5 → 6`. Nothing here parallelizes cleanly because each physics layer is a precondition for the conservation gate of the next. One modular commit per step.

---

## Properties to preserve (P1–P8)

Each is a *gate* — a test in a named step, not an aspiration. Mapped to PLAN.md invariants.

### P1 — Conservation (PLAN.md I1)
**Invariant:** `Σ nutrient + Σ (energy·χ_e) + Σ (waste·χ_w)` changes only through declared sources/sinks (injection `s`, cooling, decomposition, conversion loss), tracked in a ledger.
**Forbids:** any field mutation that doesn't debit/credit the ledger; re-deriving "truth" by re-summing instead of checking against the ledger.
**Allowed:** conversion loss `η<1` (accounted as a named sink); waste decay `δ_w` (named sink).
**Proved by:** Step 3 `test_conservation` (residual < tol over 10k ticks); Step 4 extends it across death/decomposition.

### P2 — Non-negativity (PLAN.md I2)
**Invariant:** no field concentration and no cell energy is ever negative.
**Forbids:** clamps that hide a leak (clamp must be a no-op beyond float epsilon).
**Proved by:** Step 2 (fields) and Step 3 (energy) `test_non_negativity`, asserted every tick under the debug flag.

### P3 — No free energy (PLAN.md I3)
**Invariant:** uptake/cost/emission are zero-sum moves between accounted stores; nothing creates energy or mass.
**Proved by:** Step 3 `test_no_free_energy` — a world with zero source `s` and zero forager action has a flat total; any action only *moves* quantity between stores.

### P4 — Dead-cell inertness (PLAN.md I4)
**Invariant:** `alive < θ_dead` ⇒ no uptake, no action, no emission; decomposition returns biomass exactly once, then the cell channel clears.
**Proved by:** Step 4 `test_death_and_decomposition` (dead cell takes no nutrient; decomposition credits the field exactly once).

### P5 — Determinism / replay (PLAN.md I8)
**Invariant:** same seed + same scenario ⇒ identical trajectory (byte-identical state hash at every tick).
**Forbids:** unseeded RNG, wall-clock-dependent behavior, dict-iteration-order dependence.
**Proved by:** Step 5 `test_replay` (two runs, same seed → equal per-tick hashes); Step 6 `test_pause_resume_determinism` (control timing must not change the trajectory).

### P6 — Vectorization / no per-cell loop (PLAN.md I6)
**Invariant:** the tick hot path contains no Python loop over cells; neighborhoods are shifted-tensor / stencil ops.
**Proved by:** Step 5 `test_no_cell_loop` (AST/structural scan of `env/` + `sim/tick.py` for `for`-over-grid patterns) **and** a wall-clock budget on 64×64.

### P7 — Cost coverage (PLAN.md I12)
**Invariant:** every forager action (move, uptake, signal) debits energy *before* its effect applies; no un-costed action path exists.
**Proved by:** Step 3 `test_cost_coverage` (each action reduces energy by its declared cost; a move with insufficient energy is refused, not free).

### P8 — Control-state safety (new — the web feature's gate)
**Invariant:** the controller is a well-defined bounded state machine `IDLE→RUNNING⇄PAUSED`, `RESTART→state_0`, `STOP→IDLE`; transitions are thread-safe; no stepping in PAUSED/IDLE; and the trajectory depends only on (seed, scenario, tick index) — **not** on when pause/resume happened.
**Forbids:** stepping the world from an HTTP handler thread; unbounded queues/threads; a resume that reads half-written state.
**Proved by:** Step 6 `test_controller_transitions` (illegal transitions rejected) and `test_pause_resume_determinism` (pause at tick k, resume, run to N → hash equals an uninterrupted run to N).

**Deferred properties (out of scope, named so they aren't forgotten):** thermodynamic honesty (I10) and interface groundedness (I11) gate the *learned* reward/interfaces — they land with M3/M4, not Slice 0.

---

## How to execute

- **Vertical slices, one per step.** Each step ends with something observable end-to-end (a conserved field, a forager that eats, a browser you can pause). No "build all of env/ first" horizontal mega-step.
- **Tests first.** The "Tests first" block precedes "Implementation" in every step. Write the failing test, then the code.
- **Binary acceptance.** Each gate is a passing test, an empty grep, or a committed golden hash — never "looks right."
- **Delete/replace after verify.** Not much to delete here (greenfield), but the skeleton `py_library` in `BUILD.bazel` is replaced by real targets only once they build.
- **Rewrite-from-scratch is allowed.** If a physics module fights the conservation test for >30 min, rewrite the file fresh against the test (see §B).
- **float64 for Slice 0.** Conservation headroom over long horizons matters more than speed here; revisit dtype at M2/GPU.
- **One modular commit per step**, message `thermolife(step N): <title>`, body noting tests run + green.

---

## Step 0 — Foundation

**Goal:** a buildable, testable thermolife with a dependency hub and a config loader — no domain logic.
**Why now:** every later step needs `bazel test //projects/thermolife:test_suite` to exist and a way to read `configs/*.yaml`. This unblocks everything and nothing depends on physics yet.

### Tests first
- [ ] `tests/test_config.py`: `load_world_config("configs/world.yaml")` returns a typed config with the expected keys (`grid.height==64`, `energy.eta`, a named scenario), and raises a clear error on an unknown scenario (fail-fast, no silent default).

### Implementation
- [ ] Add `thermolife_deps` `pip.parse` hub to root `MODULE.bazel` (numpy, pyyaml, pytest + its deps); commit `projects/thermolife/requirements_lock.txt` (pinned).
- [ ] `env/config.py`: dataclasses (`WorldConfig`, `FieldConfig`, `EnergyConfig`, `ScenarioConfig`) + `load_world_config(path) -> WorldConfig`. Fail-fast on missing keys / unknown scenario (raise `ConfigError`, not a default).
- [ ] `BUILD.bazel`: replace the skeleton `py_library` with a real `thermolife` lib (`env/`, `sim/` as they appear) depending on `requirement("numpy")`, `requirement("pyyaml")`; add `tests/pytest_main.py` + `pytest.ini` + a `py_test` named `test_suite`; keep the `configs` filegroup and add it to the test's `data`.

### Integration check
- [ ] `bazel test //projects/thermolife:test_suite` passes with the single config test green.

### Acceptance
- [ ] `bazel test //projects/thermolife:test_suite` exits 0.
- [ ] `grep -rn "import torch" projects/thermolife` returns empty (torch stays out of Slice 0).

**Depends on:** nothing.

---

## Step 1 — World contract

**Goal:** the `World` state object — dense SoA arrays for fields + cell channels — constructed deterministically from a config + seed.
**Why now:** the data contract must be locked before any physics reads or writes it. Everything downstream is a pure function `World → World`.

### Tests first
- [ ] `tests/test_world.py`: `from_config(cfg, seed)` yields arrays of the documented shapes/dtypes (`fields[H,W,4]` float64, `energy[H,W]`, `alive[H,W]`); a `state_hash()` is stable across two constructions with the same seed (P5 primitive) and differs when state or tick changes. **Note:** per "avoid unnecessary complexity," the `hidden[16]`/`plastic[8]`/`orient[2]` cell channels of PLAN.md §6 are *deferred to M2* (the NCA rule) — Slice-0 physics never reads them, so allocating them now would be speculative.

### Implementation
- [ ] `env/fields.py`: channel index enums (`Field.NUTRIENT`, …), `World` dataclass with `__slots__`-style dense arrays, `from_config(cfg, seed)`, `state_hash()` (hash of concatenated array bytes), `copy()`.
- [ ] Scenario source placement (static gradient) computed here from `ScenarioConfig`.

### Integration check
- [ ] `state_hash()` equal for equal seeds, unequal for unequal seeds.

### Acceptance
- [ ] `test_world.py` green; shapes/dtypes asserted; `state_hash` determinism asserted.

**Depends on:** 0.

---

## Step 2 — Field physics (`diffuse_and_decay`)

**Goal:** conservative, vectorized diffusion + decay + source injection for the physical fields.
**Why now:** fields are the substrate the forager exploits; they must move and conserve before energy accounting can trust them.

### Tests first
- [ ] `tests/test_diffusion.py`:
  - **P2 non-negativity:** after any number of steps from a non-negative field, `min >= 0`.
  - **P1 (diffusion conserves):** pure diffusion (no source, no decay) preserves total field mass to float tol.
  - **Decay is a named sink:** with decay on, total decreases by exactly the decay term (checked against a hand-computed step).
  - **Determinism:** identical field in → identical field out.
  - **Vectorized:** uses a stencil (no per-cell loop) — covered structurally in Step 5's P6 scan, referenced here.

### Implementation
- [ ] `env/diffusion.py`: `diffuse_and_decay(fields, cfg) -> fields` using a 5-point Laplacian stencil via array shifts (fixed boundary handling — reflect or zero-flux, documented). Source injection `s` for the active scenario. Cooling `δ_τ(τ−ambient)` for heat.

### Integration check
- [ ] A nutrient blob spreads and preserves mass (no source/decay); with the scenario source on, a stable gradient forms around the source cell.

### Acceptance
- [ ] `test_diffusion.py` green (P1 diffusion-conserves, P2 non-negativity, decay-exact, determinism).

**Depends on:** 1.

---

## Step 3 — Transactions + energy accounting (the conservation core)

**Goal:** `apply_conservative_transactions` — the *only* mutator of physical channels — plus the `TransactionLedger`. Uptake converts nutrient→energy (lossy `η`), actions debit energy cost-first, spending emits heat/waste.
**Why now:** this is the heart of the thermodynamics (P1/P3/P7). It must exist and be conservation-checked before the forager can act.

### Tests first
- [ ] `tests/test_conservation.py`:
  - **P1 conservation:** over 10k ticks of diffusion + a scripted uptake pattern, `|ledger_total − measured_total| < tol`.
  - **P3 no free energy:** zero source + zero action ⇒ flat total; a single uptake moves quantity nutrient→energy with `η<1` loss booked to the ledger's `conversion_loss` sink (nothing created).
  - **P7 cost coverage:** each action (move/uptake/signal) debits energy by its declared cost *before* effect; an action with `energy < cost` is refused (returns a typed `ActionRefused`, energy unchanged).
  - **P2 non-negativity:** energy never < 0 after debits.

### Implementation
- [ ] `env/transactions.py`: `TransactionLedger` (named source/sink accumulators), `apply_conservative_transactions(world, actions, cfg) -> (world, TransactionReport)`. Cost-first debit; uptake `η·min(available_nutrient, demand)`; waste `α·spent`; heat `β·spent`. Returns typed report (`ActionRefused`, `ConservationResidualExceeded`) — never a silent default (PLAN.md I-failure model).
- [ ] `env/invariants.py`: `assert_conserved(world, ledger, tol)`, `assert_non_negative(world)` — used by tests and by the debug-flag path in `tick()`.

### Integration check
- [ ] Golden-path §A (partial): fixed seed, scripted single forager uptake near the source, conservation residual < tol for 1k ticks.

### Acceptance
- [ ] `test_conservation.py` green (P1, P3, P7, P2).
- [ ] `grep -rn "except" projects/thermolife/env` shows no bare/silent excepts swallowing invariant errors.

**Depends on:** 2.

---

## Step 4 — Lifecycle (death / decomposition / inertness)

**Goal:** cells die when energy/heat/waste crosses lethal thresholds; decomposition returns biomass to nutrient exactly once; dead cells are inert.
**Why now:** the Slice-0 success gate is "the forager *dies* when the gradient is removed" — death and its conservation must be correct before that gate can be asserted.

### Tests first
- [ ] `tests/test_lifecycle.py`:
  - **P4 inertness:** a dead cell (`alive<θ_dead`) performs no uptake and emits nothing.
  - **P1 across death:** decomposition credits nutrient by exactly `decomp_return_fraction · biomass`, booked to the ledger, and the cell's energy/biomass zero out — total conserved (loss = `(1−fraction)` booked as a named sink).
  - **One-time:** decomposition fires once; a second tick on an already-decomposed cell does nothing.

### Implementation
- [ ] `env/lifecycle.py`: `apply_lifecycle(world, cfg) -> (world, TransactionReport)` — lethal-threshold death, one-time decomposition (return biomass, book loss, clear cell channels), inertness mask feeding back into `transactions` (dead cells contribute zero action).
- [ ] Population bound (P-I15) check: occupancy ≤ cap (Slice 0 has one forager, so this is a cheap assert).

### Integration check
- [ ] Golden-path §A (partial): forager with a decaying energy source eventually dies; nutrient total after decomposition matches ledger.

### Acceptance
- [ ] `test_lifecycle.py` green (P4, P1-across-death, one-time).

**Depends on:** 3.

---

## Step 5 — Forager + tick loop + Slice-0 gate

**Goal:** the hand-coded gradient-climbing forager, the full `tick()` pipeline wired in PLAN.md §10.1 order, a headless runner, and the Slice-0 success gate.
**Why now:** this closes Slice 0 — the first thing PLAN.md says to build (§15, §22). It composes Steps 1–4 into a world with real stakes.

### Tests first
- [ ] `tests/test_forager.py`: on a static gradient the forager moves toward higher nutrient (its position's nutrient is non-decreasing in expectation over K ticks) and its energy stays above lethal.
- [ ] `tests/test_slice0_gate.py` (**the headline gate, PLAN.md §15.2**): with `static_gradient`, the forager is alive at tick `removal_tick`; after the source is removed it is dead within a bounded window `W`. Asserted for a fixed seed.
- [ ] `tests/test_replay.py` (**P5**): two runs, same seed + scenario ⇒ equal per-tick `state_hash` sequence.
- [ ] `tests/test_no_cell_loop.py` (**P6**): a structural scan asserts no `for`-loop iterates grid cells in `env/*.py` or `sim/tick.py`; plus a wall-clock assert that 1k ticks on 64×64 run under a generous budget.

### Implementation
- [ ] `sim/forager.py`: hand-coded policy — read the local nutrient stencil, emit a move intent up-gradient + an uptake intent; pure function of the local neighborhood (respects locality I5).
- [ ] `sim/tick.py`: `tick(world, cfg, ledger)` in PLAN.md §10.1 order (inject → diffuse → perceive → transactions → relocate → lifecycle → invariants(debug)). Synchrony (I7) is trivial with a single forager (no cross-agent read-after-write); explicit double-buffering is deferred to the NCA rule at M2. **Config note:** implementing the gate surfaced that a persistent (non-decaying) nutrient pool + unbounded energy makes removal non-lethal — fixed by adding `nutrient.decay` (free-energy dissipation, a ledger sink) and `energy.e_max` (storage cap). Both are honest physics refinements, booked in conservation.
- [ ] `sim/runner.py`: `run(cfg, seed, ticks) -> RunResult` headless loop; `RunResult` carries per-tick hashes + a metrics record (viable biomass, conservation residual, forager energy).
- [ ] Add a `py_binary` `run` (`bazel run //projects/thermolife:run -- --scenario static_gradient --ticks 6000 --seed 42`).

### Integration check
- [ ] Golden-path §A **complete**: fixed seed, `static_gradient`, run to `removal_tick+W`; assert (a) conservation residual < tol throughout, (b) forager alive before removal, (c) forager dead after, (d) the run's terminal `state_hash` equals a committed golden constant.

### Acceptance
- [ ] `test_forager.py`, `test_slice0_gate.py`, `test_replay.py`, `test_no_cell_loop.py` all green.
- [ ] `bazel run //projects/thermolife:run -- --scenario static_gradient --ticks 200 --seed 42` prints per-tick conservation residual and exits 0.
- [ ] PLAN.md §15.2 gate demonstrably holds (forager dies on gradient removal).

**Depends on:** 4.

---

## Step 6 — Web control endpoint (Tailscale)

**Goal:** a small stdlib web server that runs the sim in a background thread and exposes **start / pause / restart / stop / state**, watchable in a browser and reachable over Tailscale.
**Why now:** it sits on the runnable loop from Step 5 — you can't control what can't run. It's the user-facing deliverable.

### Tests first
- [ ] `tests/test_controller.py` (**P8**): drive `SimController` directly (no HTTP):
  - `test_controller_transitions`: legal transitions succeed; illegal ones (`pause` while `IDLE`, `step` while `PAUSED`) return a typed error, not a crash or silent no-op.
  - `test_pause_resume_determinism`: start(seed) → run to tick k → pause → resume → run to N; the tick-N `state_hash` equals an uninterrupted run(seed) to N. (Control timing must not perturb the trajectory.)
  - `test_restart_reseeds`: restart returns to `state_0` (tick 0 hash equals the fresh-construction hash).
- [ ] `tests/test_server.py`: with the server bound to `127.0.0.1:0` (ephemeral port) in-process, `POST /start`, `/pause`, `/resume`, `/restart`, `/stop` drive the controller and `GET /state` returns JSON with the documented schema (`tick`, `status`, `residual`, `nutrient` + `occupancy` as nested lists sized `H×W`). No Tailscale needed for the test — it's a loopback socket.

### Implementation
- [ ] `sim/controller.py`: `SimController` — owns the single background sim thread and the state machine (`IDLE/RUNNING/PAUSED`), guarded by a `threading.Lock` + a `threading.Event` for pause. The thread is the **only** stepper (P8: HTTP handlers never touch the world). Bounded: one thread, one world, no queues. `start(seed, scenario)`, `pause()`, `resume()`, `restart()`, `stop()`, `snapshot() -> dict`.
- [ ] `sim/server.py`: stdlib `http.server.ThreadingHTTPServer` + a `BaseHTTPRequestHandler` routing the control POSTs and `GET /state` / `GET /` (serves `viewer.html`). Handlers only call `SimController` methods. Typed 4xx on illegal transition. Bind host/port from CLI (`--host 127.0.0.1 --port 8787`).
- [ ] `sim/viewer.html`: a single self-contained page — a `<canvas>` that polls `GET /state` (~5 Hz), draws nutrient as a heatmap + the forager cell, and has Start / Pause / Resume / Restart / Stop buttons hitting the control endpoints. No external assets (CSP-clean, works offline).
- [ ] `py_binary` `serve` (`bazel run //projects/thermolife:serve -- --port 8787`); include `viewer.html` in its `data`.
- [ ] Docs: a `sim/README.md` section — expose on the tailnet with `tailscale serve --bg 8787` (private to your tailnet; default), or `tailscale funnel 8787` for public internet (opt-in, noted as a security decision). The app binds loopback; Tailscale proxies — **no Tailscale code in the app** (keeps it simple + testable).

### Integration check
- [ ] Manual: `bazel run //projects/thermolife:serve`, then `tailscale serve --bg 8787`; open the tailnet URL, click Start → grid animates, Pause → freezes, Restart → resets to tick 0, Stop → idle. (Manual because it needs a live tailnet; the automated `test_server.py` covers the API over loopback.)

### Acceptance
- [ ] `test_controller.py` (P8: transitions, pause/resume determinism, restart-reseed) and `test_server.py` green.
- [ ] `bazel test //projects/thermolife:test_suite` fully green (all of Steps 0–6).
- [ ] `sim/README.md` documents the `tailscale serve` / `funnel` commands and the private-vs-public decision.
- [ ] PLAN.md §11 updated to mention the `sim/` package.

**Depends on:** 5.

---

## §A — Golden-path integration test (the spine)

```
GIVEN  seed=42, scenario=static_gradient (source at (16,16), removal_tick=R, window W)
WHEN   sim/runner.run(cfg, seed, ticks=R+W) executes the full tick() pipeline
THEN   conservation residual < tol at EVERY tick                         (P1)
AND    fields and energy are non-negative at every tick                  (P2)
AND    the forager is alive at tick R-1                                  (stakes)
AND    the forager is dead by tick R+W                                   (stakes, §15.2)
AND    the terminal state_hash equals a committed golden constant        (P5)
```

Runs after every step from Step 3 onward. Goes red ⇒ the most recent step broke it. **Golden decision (implemented):** rather than a brittle hardcoded terminal-hash literal (fragile across numpy versions), the "golden" is the *determinism-checked* terminal hash — two same-seed runs must agree (P5) — reproducible under the pinned hermetic interpreter. The physical stakes (alive-before / dead-after / residual-bounded) are the content gate.

## §B — Iteration loop

```
Read the failing assertion verbatim
        │
   Is the test's invariant correct?  ──No──▶ fix the test, note why in the commit
        │ Yes
        ▼
   Fix impl — minimum change, OR rewrite the file fresh against the test (whichever is faster)
        │
        ▼
   Re-run the failing test → run golden path §A → green ⇒ done
```

**Stuck > 30 min on the same failure:** stop; write expected-vs-observed in the commit draft; print actual array totals (then revert the print); re-read the step's Acceptance; **consider rewriting the offending module from scratch against its test** (often faster than untangling a conservation leak). Do not start the next step while stuck. A single-file rewrite is a valid escape, not scope creep.

## §C — Out of scope (deferred to PLAN.md M1–M7)

The NCA cell rule (`model/cell_core.py`), learned ligand/receptor interfaces + binding, the local predictor, online plasticity (`z`), the average-reward objective + soft barriers, TBPTT training (`train/`), the nonstationarity curriculum, reproduction/evolution, particles/radius-graph, **torch, GPU, matplotlib**, multiple cell types beyond the single forager, and any *learned* reward — so properties I10 (thermodynamic honesty) and I11 (interface groundedness) are **not** gated here. Web-endpoint auth is out of scope: access control is delegated to the Tailscale tailnet (ACLs), not built into the app. The moving-source / shock / heat-wave scenarios in `world.yaml` (`first_experiment`) are exercised at M2+; Slice 0 uses `static_gradient` only.

## §D — Design tensions surfaced for review

**D1. Web framework: stdlib `http.server` vs FastAPI+uvicorn.**
Options: (a) stdlib — zero pip deps, hermetic, trivially bazel-testable, but manual routing and no async; (b) FastAPI+uvicorn — ergonomic, async streaming (SSE/WebSocket), but adds several deps + an ASGI server to the hermetic build.
**Recommendation: (a) stdlib.** The control surface is five POSTs + one polled GET; a `<canvas>` polling at ~5 Hz is ample for a 64×64 grid. This directly honors "avoid unnecessary complexity." Revisit if we later want high-FPS streaming of large grids.

**D2. Tailscale exposure: `serve` (tailnet-private) vs `funnel` (public internet).**
Options: (a) `tailscale serve` — reachable only by your own devices/tailnet, no public exposure; (b) `tailscale funnel` — a public HTTPS URL anyone can hit.
**Recommendation: (a) `serve` by default**, document `funnel` as an explicit opt-in with a security note. "On the web where I can control it" is satisfied by the tailnet without exposing an unauthenticated sim-control API to the internet. The app is unauthenticated by design (D-scope), so `funnel` without adding auth would be an open control endpoint — flag before enabling.

**D3. Viewer rendering: client-side `<canvas>` (JSON) vs server-side PNG.**
Options: (a) canvas from `/state` JSON — no server-side image deps; (b) server renders PNG frames (matplotlib/Pillow) — heavier deps, more bandwidth.
**Recommendation: (a) canvas.** Keeps the server dep-free (no matplotlib) and the payload small (send nutrient + occupancy as `H×W` arrays; ~4 KB for 64×64). Grounded interface shapes (I11) are an M3 viz concern, not Slice 0.

**D4. Field dtype: float64 vs float32.**
Recommendation: **float64** for Slice 0 — conservation residual headroom over 10k+ ticks beats speed on a 64×64 CPU grid. Reconsider at M2 when torch/GPU enter and float32 matters for throughput.

**D5. `sim/` vs reusing `train/`.**
The operational loop + control + server are *not* the future TBPTT training loop. Recommendation: **new `sim/` package**; document the split in PLAN.md §11 so `train/` stays reserved for M2+ meta-training.

## Definition of done (whole plan)

- [ ] `bazel test //projects/thermolife:test_suite` green: config, world, diffusion, conservation (P1/P3/P7/P2), lifecycle (P4), forager, slice0-gate, replay (P5), no-cell-loop (P6), controller (P8), server.
- [ ] Golden-path §A green with a committed terminal `state_hash`.
- [ ] `bazel run //projects/thermolife:run -- --scenario static_gradient --ticks 6000 --seed 42` completes; forager relocates on the gradient and dies when it's removed.
- [ ] `bazel run //projects/thermolife:serve` + `tailscale serve --bg 8787` yields a tailnet URL with working Start / Pause / Restart / Stop and a live grid.
- [ ] `grep -rn "import torch" projects/thermolife` empty; PLAN.md §11 mentions `sim/`; `sim/README.md` documents the Tailscale commands + the serve-vs-funnel decision.
- [ ] Seven modular commits (`thermolife(step 0..6): …`), each green at the time of commit.
