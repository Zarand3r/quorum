"""FastAPI server exposing the toy v1 sim as an animated single-page app.

Endpoints:

  GET  /              – single-page HTML app (SVG grid + Chart.js metric).
  GET  /api/run       – run one sim end-to-end and return JSON:
                          {config, cells_history, metrics}.
  GET  /healthz       – liveness probe.

Bounds are enforced on all query params so a public URL cannot be used to
burn compute. All state is per-request; no shared mutable state, no LLM
backend (public traffic → mock policy only). Uvicorn binds by default to
127.0.0.1; front the process with Tailscale Serve / Funnel for a public
URL.

Run:

  bazel run //projects/quorum/experiments:viz -- \\
      --host 127.0.0.1 --port 8081 --path /quorum

Then serve on the tailnet:

  tailscale funnel --bg --set-path=/quorum http://127.0.0.1:8081
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Sequence

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

from toy_v1 import runner
from toy_v1.policy import MockPolicy, Policy, SchellingRulePolicy


LOGGER = logging.getLogger("toy_v1.viz")


# ---------- bounds on public traffic ----------

# Keep these tight enough that a run stays fast (< 1 s) on any hardware.
# The mock backend is the only policy this server ever instantiates.
MAX_GRID_SIZE = 32
MAX_N_AGENTS = 500
MAX_TICKS = 400


# ---------- app factory ----------


def make_app(root_path: str = "") -> FastAPI:
    """Build the FastAPI app. ``root_path`` matches the ``--set-path`` used by
    the tailscale funnel so client-side links resolve correctly."""
    app = FastAPI(
        title="quorum toy v1 — LLM Schelling sim viz",
        docs_url=None,       # no Swagger; public URL
        redoc_url=None,
        openapi_url=None,
        root_path=root_path,
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/run")
    def api_run(
        seed: int = Query(42),
        n_agents: int = Query(30, ge=1),
        grid_size: int = Query(8, ge=2),
        ticks: int = Query(40, ge=1),
        policy: str = Query("schelling"),
        p_stay: float = Query(0.5, ge=0.0, le=1.0),
        threshold: float = Query(0.3, ge=0.0, le=1.0),
    ) -> JSONResponse:
        if grid_size > MAX_GRID_SIZE:
            raise HTTPException(422, f"grid_size must be ≤ {MAX_GRID_SIZE}")
        if n_agents > MAX_N_AGENTS:
            raise HTTPException(422, f"n_agents must be ≤ {MAX_N_AGENTS}")
        if ticks > MAX_TICKS:
            raise HTTPException(422, f"ticks must be ≤ {MAX_TICKS}")
        if n_agents > grid_size * grid_size:
            raise HTTPException(422, "n_agents exceeds grid capacity")

        cfg = runner.RunConfig(
            grid_size=grid_size,
            n_agents=n_agents,
            n_ticks=ticks,
            seed=seed,
        )
        backend: Policy = _make_policy(policy, seed=seed, p_stay=p_stay, threshold=threshold)
        result = runner.run(cfg, backend)
        return JSONResponse(_serialize(result, policy_name=policy))

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse(_INDEX_HTML.replace("__ROOT_PATH__", root_path or ""))

    return app


# ---------- serialization ----------


def _serialize(result: runner.RunResult, *, policy_name: str) -> dict[str, Any]:
    """Encode a RunResult as JSON-safe primitives. cells_history is a
    ``list[list[list[int]]]`` — one frame per tick+1 entry."""
    return {
        "config": {
            "grid_size": result.config.grid_size,
            "n_agents": result.config.n_agents,
            "n_ticks": result.config.n_ticks,
            "seed": result.config.seed,
            "policy": policy_name,
        },
        "cells_history": [c.tolist() for c in result.cells_history],
        "metrics": [
            {
                "t": m.t,
                "same_color_fraction": m.same_color_fraction,
                "movers": m.movers,
                "fwd_passes": m.fwd_passes,
            }
            for m in result.metrics
        ],
    }


# ---------- policy dispatch ----------


def _make_policy(name: str, *, seed: int, p_stay: float, threshold: float) -> Policy:
    if name == "mock":
        return MockPolicy(seed=seed, p_stay=p_stay)
    if name == "schelling":
        return SchellingRulePolicy(threshold=threshold)
    raise HTTPException(422, f"unknown policy {name!r}; expected mock|schelling")


# ---------- CLI ----------


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8081)
    p.add_argument(
        "--path", default="",
        help=(
            "URL prefix matching the tailscale --set-path value "
            "(e.g. '/quorum'). Empty for root."
        ),
    )
    p.add_argument("--log-level", default="info", choices=("critical", "error", "warning", "info", "debug"))
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    app = make_app(root_path=args.path)
    LOGGER.info("serving on http://%s:%d (root_path=%r)", args.host, args.port, args.path or "/")
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


# ---------- inline SPA ----------

# Single-file HTML — deliberately no build step. The JS is small enough to
# read; it renders an SVG grid and a Chart.js line for same_color_fraction.
# `__ROOT_PATH__` is substituted at request time so the JS calls the API
# under the same prefix Tailscale is proxying.
_INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>quorum toy v1 — LLM Schelling sim</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #0b0d10; color: #d7dde3;
         font: 14px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; }
  header { padding: 12px 16px; border-bottom: 1px solid #1c2127;
           display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  h1 { font-size: 15px; margin: 0; font-weight: 600; color: #e9eef3; }
  h1 small { color: #7a8592; font-weight: 400; margin-left: 8px; }
  .ctl { display: flex; gap: 6px; align-items: center; }
  .ctl label { color: #7a8592; }
  input[type="number"] { width: 68px; padding: 3px 6px;
    background: #12161c; color: #d7dde3; border: 1px solid #1c2127;
    border-radius: 4px; font: inherit; }
  input[type="range"] { width: 120px; }
  button { background: #2a67ff; color: #fff; border: 0; padding: 5px 12px;
    border-radius: 4px; font: inherit; cursor: pointer; }
  button:disabled { background: #2a2f36; color: #7a8592; cursor: default; }
  .grid-wrap { padding: 16px; display: grid;
    grid-template-columns: minmax(300px, 480px) 1fr; gap: 16px;
    height: calc(100vh - 60px); }
  #grid { width: 100%; height: auto; background: #12161c;
    border: 1px solid #1c2127; border-radius: 6px; }
  #chart-wrap { background: #12161c; border: 1px solid #1c2127;
    border-radius: 6px; padding: 10px; display: flex; flex-direction: column; }
  #chart { flex: 1; min-height: 200px; }
  #status { color: #7a8592; padding: 8px 4px 0; }
  #status b { color: #e9eef3; }
  .grid-panel { position: relative; }
  #tick-badge {
    position: absolute; top: 10px; left: 10px;
    background: rgba(11, 13, 16, 0.85);
    border: 1px solid #1c2127;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e9eef3;
    font-size: 15px; font-weight: 600;
    letter-spacing: 0.3px;
    pointer-events: none;
  }
  #tick-badge .lbl { color: #7a8592; font-weight: 400; margin-right: 4px; }
  #tick-badge .num { color: #6b8fff; font-variant-numeric: tabular-nums; }
  #tick-badge .sep { color: #3a3f47; margin: 0 2px; }
  #tick-badge .tot { color: #a5adb7; font-variant-numeric: tabular-nums; }
  .about { padding: 10px 16px; color: #7a8592; font-size: 12px;
    border-top: 1px solid #1c2127; }
  .about a { color: #6b8fff; text-decoration: none; }
</style>
</head>
<body>
<header>
  <h1>quorum toy v1 <small>Schelling sim · pick a backend</small></h1>
  <span class="ctl"><label>policy</label>
    <select id="policy">
      <option value="schelling" selected>schelling rule (produces segregation)</option>
      <option value="mock">mock (random baseline · no emergence)</option>
    </select>
  </span>
  <span class="ctl" id="ctl_threshold"><label>τ</label><input id="threshold" type="range" min="0" max="1" step="0.05" value="0.3"><span id="threshold_val">0.30</span></span>
  <span class="ctl" id="ctl_p_stay" style="display:none"><label>p_stay</label><input id="p_stay" type="range" min="0" max="1" step="0.05" value="0.5"><span id="p_stay_val">0.50</span></span>
  <span class="ctl"><label>seed</label><input id="seed" type="number" value="42"></span>
  <span class="ctl"><label>grid</label><input id="grid_size" type="number" value="16" min="2" max="32"></span>
  <span class="ctl"><label>agents</label><input id="n_agents" type="number" value="120" min="1" max="500"></span>
  <span class="ctl"><label>ticks</label><input id="ticks" type="number" value="120" min="1" max="400"></span>
  <span class="ctl"><label>fps</label><input id="fps" type="range" min="1" max="30" step="1" value="8"></span>
  <button id="go">run</button>
  <button id="pause" disabled>pause</button>
</header>
<div class="grid-wrap">
  <div class="grid-panel">
    <svg id="grid" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet"></svg>
    <div id="tick-badge">
      <span class="lbl">tick</span><span class="num" id="tick-num">—</span><span class="sep">/</span><span class="tot" id="tick-tot">—</span>
    </div>
  </div>
  <div id="chart-wrap">
    <canvas id="chart"></canvas>
    <div id="status">idle</div>
  </div>
</div>
<div class="about">
  Two backends via the same <code>Policy</code> protocol.
  <b>schelling rule</b> — move iff same-color-fraction of non-empty neighbors &lt; τ.
  Classic Schelling; expect the same-color chart to rise from ~0.5 → ~0.85 and
  visible RED/BLUE islands.
  <b>mock</b> — Bernoulli coin flip at <code>p_stay</code>; ignores the grid;
  same-color stays near 0.5. This is the null baseline the design doc calls
  for. Bounds: grid ≤ 32, agents ≤ 500, ticks ≤ 400. Source:
  <a href="https://github.com/Zarand3r/quorum">Zarand3r/quorum</a>.
</div>
<script>
const ROOT = "__ROOT_PATH__";  // e.g. "/quorum" or ""
const $ = (id) => document.getElementById(id);
const svg = $("grid");
let chart = null;

// --- animation state (module-scoped so togglePause can restart the loop) ---
let animId = null;       // pending setTimeout handle
let paused = false;
let animIdx = 0;         // next frame index to render
let animTotal = 0;       // history.length - 1
let animHistory = null;  // list[list[list[int]]]
let animMetrics = null;  // list[{t, same_color_fraction, movers, ...}]
let animGridSize = 8;

function makeChart() {
  const ctx = $("chart").getContext("2d");
  return new Chart(ctx, {
    type: "line",
    data: { labels: [], datasets: [{
      label: "same-color fraction",
      data: [],
      borderColor: "#6b8fff",
      backgroundColor: "rgba(107, 143, 255, 0.15)",
      pointRadius: 0,
      tension: 0.15,
      fill: true,
    }]},
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      scales: {
        x: { title: {display: true, text: "tick", color: "#7a8592"},
             ticks: {color: "#7a8592"}, grid: {color: "#1c2127"} },
        y: { min: 0, max: 1, title: {display: true, text: "fraction", color: "#7a8592"},
             ticks: {color: "#7a8592"}, grid: {color: "#1c2127"} },
      },
      plugins: { legend: { labels: { color: "#d7dde3" } } },
    },
  });
}

function renderFrame(cells, gridSize) {
  svg.setAttribute("viewBox", `0 0 ${gridSize} ${gridSize}`);
  const parts = [];
  for (let r = 0; r < gridSize; r++) {
    for (let c = 0; c < gridSize; c++) {
      const v = cells[r][c];
      const color = v === 0 ? "#1c2127" : v === 1 ? "#ff5a5a" : "#6b8fff";
      parts.push(`<rect x="${c}" y="${r}" width="1" height="1" fill="${color}"/>`);
    }
  }
  svg.innerHTML = parts.join("");
}

function statusLine(t, tot, frac, movers) {
  $("status").innerHTML =
    `same-color <b>${frac.toFixed(3)}</b> · movers <b>${movers}</b> · <b>fwd_passes=1</b>`;
}

function updateTickBadge(t, tot) {
  $("tick-num").textContent = t;
  $("tick-tot").textContent = tot;
}

// Render one frame + advance if not paused. Reads from module-scoped
// animation state so togglePause() can resume by re-invoking this.
function stepAnim() {
  if (paused) return;
  renderFrame(animHistory[animIdx], animGridSize);
  updateTickBadge(animIdx, animTotal);
  if (animIdx === 0) {
    statusLine(0, animTotal, 0.0, 0);
  } else {
    const m = animMetrics[animIdx - 1];
    statusLine(animIdx, animTotal, m.same_color_fraction, m.movers);
    chart.data.labels.push(m.t);
    chart.data.datasets[0].data.push(m.same_color_fraction);
    chart.update("none");
  }
  if (animIdx < animTotal) {
    animIdx++;
    const fps = parseInt($("fps").value, 10) || 8;
    animId = setTimeout(stepAnim, 1000 / fps);
  } else {
    $("go").disabled = false;
    $("pause").disabled = true;
    $("status").innerHTML += " · <b>done</b>";
  }
}

async function run() {
  $("go").disabled = true;
  $("pause").disabled = false;
  paused = false;
  $("pause").textContent = "pause";
  if (animId) { clearTimeout(animId); animId = null; }

  const params = new URLSearchParams({
    seed: $("seed").value,
    grid_size: $("grid_size").value,
    n_agents: $("n_agents").value,
    ticks: $("ticks").value,
    policy: $("policy").value,
    p_stay: $("p_stay").value,
    threshold: $("threshold").value,
  });
  $("status").textContent = "running sim…";
  let payload;
  try {
    const res = await fetch(`${ROOT}/api/run?${params}`);
    if (!res.ok) {
      const err = await res.text();
      $("status").textContent = `error: ${err}`;
      $("go").disabled = false; $("pause").disabled = true;
      return;
    }
    payload = await res.json();
  } catch (e) {
    $("status").textContent = `fetch error: ${e}`;
    $("go").disabled = false; $("pause").disabled = true;
    return;
  }

  animHistory  = payload.cells_history;
  animMetrics  = payload.metrics;
  animGridSize = payload.config.grid_size;
  animTotal    = animHistory.length - 1;   // history has n_ticks+1 frames
  animIdx      = 0;

  chart.data.labels = [];
  chart.data.datasets[0].data = [];
  chart.update();
  updateTickBadge(0, animTotal);

  stepAnim();
}

function togglePause() {
  paused = !paused;
  $("pause").textContent = paused ? "resume" : "pause";
  if (!paused && animHistory && animIdx <= animTotal) {
    // Kick the loop again from where it stopped.
    stepAnim();
  }
}

// Wire controls
$("p_stay").addEventListener("input", (e) => {
  $("p_stay_val").textContent = parseFloat(e.target.value).toFixed(2);
});
$("threshold").addEventListener("input", (e) => {
  $("threshold_val").textContent = parseFloat(e.target.value).toFixed(2);
});
$("policy").addEventListener("change", (e) => {
  const p = e.target.value;
  $("ctl_threshold").style.display = (p === "schelling") ? "" : "none";
  $("ctl_p_stay").style.display    = (p === "mock")      ? "" : "none";
});
$("go").addEventListener("click", () => { if (animId) clearTimeout(animId); run(); });
$("pause").addEventListener("click", togglePause);

// Init
window.addEventListener("DOMContentLoaded", () => {
  chart = makeChart();
  // Render an empty grid so the page has something visible before first run.
  renderFrame(Array.from({length: 8}, () => Array(8).fill(0)), 8);
  $("status").textContent = "idle · click run";
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
