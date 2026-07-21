"""Live viewer for MEMBRANE self-assembly — watch amphiphiles order into a one-particle-thick band.

Self-contained (inline HTML, canvas): steps a MembraneEngine in a background thread and pushes state
over Server-Sent Events (one persistent connection, no per-frame round-trip). Water = hollow blue
dots; lipids = a dot (head) with a stalk toward the tail (+o). A few physical knobs are live; the
metric strip shows director order S, side-by-side fraction, sheet aspect, and cluster count.

    bazel run //projects/vivarium:serve_membrane
    bazel run //projects/vivarium:serve_membrane -- --port 8082
    # expose on your tailnet:  tailscale serve --bg <port>
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

from membrane import MembraneEngine
from lipid_rod import RodEngine
from charged import ChargedEngine

# live knobs — physical laws only (measure-don't-reward: the metric never feeds these). One tuple per
# engine; the frontend renders exactly these sliders and posts them back by attribute name.
_KNOBS_ROD = ("k_att", "wc", "temp", "mu")
_KNOBS_MEMBRANE = ("ga", "gi", "gc", "kappa", "torque", "temp")
_KNOBS_CHARGED = ("k_e", "k_rep", "temp", "mu")


class Sim:
    """Steps a membrane engine in a background thread; publishes the latest snapshot."""

    def __init__(self, seed: int, hz: float, steps_per_frame: int, make_engine, knobs) -> None:
        self.seed = seed
        self.hz = hz
        self.stream_hz = min(30.0, hz)
        self.steps_per_frame = steps_per_frame
        self.make_engine = make_engine
        self.knobs = knobs
        self.lock = threading.Lock()
        self.engine = make_engine(seed)
        self.paused = False
        self._stop = False
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        dt = 1.0 / self.hz
        while not self._stop:
            t0 = time.perf_counter()
            if not self.paused:
                with self.lock:
                    for _ in range(self.steps_per_frame):
                        self.engine.step()
            time.sleep(max(0.0, dt - (time.perf_counter() - t0)))

    def state(self) -> dict:
        with self.lock:
            e = self.engine
            m = e.measure()
            out = {
                "t": e.t,
                "L": e.L,
                "bound": e.pos_bound,
                "pos": [[round(float(x), 3), round(float(y), 3)] for x, y in e.pos],
                "species": [int(s) for s in e.species],
                "orient": [[round(float(x), 3), round(float(y), 3)] for x, y in e.orient],
                "metrics": m,
                "knob_names": list(self.knobs),
                "knobs": {k: round(float(getattr(e, k)), 4) for k in self.knobs if hasattr(e, k)},
            }
            if hasattr(e, "view_points"):   # charged engine: send charge points + lipid whiskers
                pts, whisk = e.view_points()
                out["points"], out["whiskers"] = pts, whisk
            return out

    def set_knobs(self, updates: dict) -> None:
        with self.lock:
            for k in self.knobs:
                if k in updates and hasattr(self.engine, k):
                    try:
                        setattr(self.engine, k, max(0.0, float(updates[k])))
                    except (TypeError, ValueError):
                        pass

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def restart(self, same: bool) -> None:
        with self.lock:
            saved = {k: getattr(self.engine, k) for k in self.knobs if hasattr(self.engine, k)}
            self.seed = self.seed if same else self.seed + 1
            self.engine = self.make_engine(self.seed)
            for k, v in saved.items():
                if hasattr(self.engine, k):
                    setattr(self.engine, k, v)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a) -> None:
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.endswith("/stream"):
            self._stream()
        elif self.path.endswith("/state"):
            self._send(200, json.dumps(self.server.sim.state()).encode(), "application/json")
        else:
            self._send(200, _PAGE.encode(), "text/html; charset=utf-8")

    def _stream(self) -> None:
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            dt = 1.0 / self.server.sim.stream_hz
            while not self.server.sim._stop:
                payload = json.dumps(self.server.sim.state())
                self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.flush()
                time.sleep(dt)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def do_POST(self) -> None:
        from urllib.parse import parse_qs, urlparse
        sim = self.server.sim
        path = self.path.split("?", 1)[0]
        q = parse_qs(urlparse(self.path).query)
        if path.endswith("/pause"):
            sim.set_paused(True)
        elif path.endswith("/resume"):
            sim.set_paused(False)
        elif path.endswith("/restart"):
            sim.restart(same="same" in q)
        elif path.endswith("/set"):
            sim.set_knobs({k: v[0] for k, v in q.items()})
        else:
            self._send(404, b"not found", "text/plain")
            return
        self._send(200, b"{}", "application/json")


_PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>vivarium — membranes</title>
<style>
 body{margin:0;background:#0b1220;color:#cbd5e0;font-family:ui-monospace,Menlo,monospace}
 #wrap{display:flex;gap:16px;padding:16px;flex-wrap:wrap}
 canvas{background:#0b1220;border:1px solid #1e293b;border-radius:8px}
 #side{min-width:260px;max-width:320px}
 h1{font-size:15px;margin:0 0 4px} .sub{font-size:12px;color:#64748b;margin:0 0 12px}
 .m{font-size:13px;line-height:1.7} .m b{color:#f6ad55}
 .row{display:flex;align-items:center;gap:8px;margin:7px 0;font-size:12px}
 .row label{width:52px;color:#94a3b8} .row input{flex:1}
 .row span{width:38px;text-align:right;color:#e2e8f0}
 button{background:#1e293b;color:#cbd5e0;border:1px solid #334155;border-radius:6px;
   padding:6px 10px;font-family:inherit;font-size:12px;cursor:pointer;margin:2px}
 button:hover{background:#334155}
</style></head><body><div id="wrap">
 <canvas id="c" width="640" height="640"></canvas>
 <div id="side">
  <h1>charged self-assembly</h1>
  <p class="sub">tokens are charged shapes — negative centre (blue), positive lobes (red). water is
  radially polar; a lipid is water with a neutral tail (grey). polarity from the shape; no dictated
  bonds; conservative (β=0), so it settles.</p>
  <div class="m" id="metrics"></div>
  <div id="knobs" style="margin-top:14px"></div>
  <div style="margin-top:10px">
   <button onclick="post('/pause')">pause</button>
   <button onclick="post('/resume')">resume</button>
   <button onclick="post('/restart')">new seed</button>
   <button onclick="post('/restart?same=1')">replay</button>
  </div>
  <p class="sub" style="margin-top:14px">+ charge red · − charge blue · neutral tail grey · grey line =
  a lipid's head→tail axis. temp anneals to 0; nudge it up to melt &amp; re-anneal, or raise coulomb.</p>
 </div>
</div>
<script>
const cv=document.getElementById('c'), ctx=cv.getContext('2d'), W=cv.width;
// mounted at / or under a prefix (e.g. /vivarium) — resolve endpoints against the page path so the
// stream/POSTs hit THIS server through the tailscale funnel, not the root proxy.
const BASE = location.pathname.replace(/\/$/, '');
// per-knob [label, min, max, step, decimals] — covers both engines; only the ones the server sends appear.
const KNOB={k_att:['attract',0,4,0.1,2], wc:['range',1.0,2.2,0.05,2], temp:['temp',0,0.25,0.01,2],
  mu:['mobility',0.002,0.02,0.001,3], ga:['attract',0,0.8,0.01,2], gi:['inter',0,4,0.1,2],
  gc:['cohere',0,0.08,0.005,3], kappa:['rod κ',0,8,0.5,1], torque:['torque',0,0.6,0.02,2],
  k_e:['coulomb',0.1,2.5,0.05,2], k_rep:['exclude',1.0,4.0,0.1,1]};
let KN=null, dragging=false;
function buildKnobs(names){
  KN=names; const box=document.getElementById('knobs'); box.innerHTML='';
  for(const k of names){ const [lab,mn,mx,st,dc]=KNOB[k]||[k,0,1,0.01,2];
    const row=document.createElement('div'); row.className='row';
    row.innerHTML=`<label>${lab}</label><input id="${k}" type="range" min="${mn}" max="${mx}" step="${st}"><span id="${k}_v"></span>`;
    box.appendChild(row); const el=document.getElementById(k);
    el.dataset.dc=dc;
    el.addEventListener('input',()=>{document.getElementById(k+'_v').textContent=(+el.value).toFixed(dc);});
    el.addEventListener('mousedown',()=>dragging=true);
    el.addEventListener('change',()=>{dragging=false; fetch(BASE+'/set?'+k+'='+el.value,{method:'POST'});});
  }
}
function post(p){fetch(BASE+p,{method:'POST'});}
function draw(s){
  if(!KN && s.knob_names) buildKnobs(s.knob_names);
  ctx.clearRect(0,0,W,W); const B=s.bound, sc=W/(2*B);
  const X=x=>(x+B)*sc, Y=y=>(y+B)*sc;
  if(s.points){ drawCharged(s,X,Y); }
  else {
    ctx.strokeStyle='rgba(43,108,176,0.5)'; ctx.lineWidth=1;
    for(let i=0;i<s.pos.length;i++){ if(s.species[i]!==0) continue;
      const p=s.pos[i]; ctx.beginPath(); ctx.arc(X(p[0]),Y(p[1]),3,0,7); ctx.stroke(); }
    const stalk=0.55;
    for(let i=0;i<s.pos.length;i++){ if(s.species[i]!==1) continue;
      const p=s.pos[i], o=s.orient[i];
      const cx=X(p[0]),cy=Y(p[1]),tx=X(p[0]+stalk*o[0]),ty=Y(p[1]+stalk*o[1]);
      if(Math.abs(tx-cx)<W/2 && Math.abs(ty-cy)<W/2){
        ctx.strokeStyle='rgba(246,173,85,0.85)'; ctx.lineWidth=2;
        ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(tx,ty); ctx.stroke();
        ctx.fillStyle='#f6ad55'; ctx.beginPath(); ctx.arc(tx,ty,1.7,0,7); ctx.fill(); }
      ctx.fillStyle='#e53e3e'; ctx.beginPath(); ctx.arc(cx,cy,3.4,0,7); ctx.fill(); }
  }
  const m=s.metrics;
  const line = ('demix' in m)
    ? `t = <b>${s.t}</b><br>demix (tails buried) = <b>${m.demix.toFixed(3)}</b> (→1)<br>`+
      `side-by-side = <b>${m.side.toFixed(3)}</b><br>aggregates = <b>${m.n_lipid_clusters}</b>`
    : `t = <b>${s.t}</b><br>director order S = <b>${m.S.toFixed(3)}</b> (→1 aligned)<br>`+
      `side-by-side = <b>${m.side.toFixed(3)}</b> (→1 = beside, not stacked)<br>`+
      `sheet aspect = <b>${m.sheetness.toFixed(2)}</b><br>aggregates = <b>${m.n_lipid_clusters}</b>`;
  document.getElementById('metrics').innerHTML = line;
  if(!dragging && KN) for(const k of KN){ const el=document.getElementById(k);
    if(el && k in s.knobs){ el.value=s.knobs[k];
      document.getElementById(k+'_v').textContent=(+s.knobs[k]).toFixed(+el.dataset.dc);} }
}
function drawCharged(s,X,Y){
  for(const w of s.whiskers){ const hx=X(w[0]),hy=Y(w[1]),tx=X(w[2]),ty=Y(w[3]);
    if(Math.abs(hx-tx)<W/2 && Math.abs(hy-ty)<W/2){
      ctx.strokeStyle='#334155'; ctx.lineWidth=1.5;
      ctx.beginPath(); ctx.moveTo(hx,hy); ctx.lineTo(tx,ty); ctx.stroke(); } }
  for(const p of s.points){ const x=X(p[0]),y=Y(p[1]),sg=p[2];
    ctx.fillStyle = sg>0?'#e53e3e':(sg<0?'#3b82f6':'#64748b');
    const r = sg<0?3.6:(sg>0?2.6:3.0);
    ctx.beginPath(); ctx.arc(x,y,r,0,7); ctx.fill(); }
}
const es=new EventSource(BASE+'/stream');
es.onmessage=e=>draw(JSON.parse(e.data));
</script></body></html>"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="vivarium membrane live viewer")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8082)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--hz", type=float, default=30.0)
    p.add_argument("--steps-per-frame", type=int, default=10,
                   help="engine steps per rendered frame (assembly takes ~16k steps)")
    p.add_argument("--N", type=int, default=None)
    p.add_argument("--engine", choices=["charged", "rod", "legacy"], default="charged",
                   help="charged: neg-centre/pos-lobe tokens + water (polarity from shape); "
                        "rod: rigid multi-bead lipids (micelles); legacy: single-bead nematic (streams)")
    a = p.parse_args(argv)
    if a.engine == "legacy":
        N = a.N if a.N is not None else 96
        make_engine = lambda s: MembraneEngine(s, N=N)  # noqa: E731
        knobs = _KNOBS_MEMBRANE
        label = "membrane.py (single-bead anisotropic — flowing nematic)"
    elif a.engine == "rod":
        N = a.N if a.N is not None else 90
        make_engine = lambda s: RodEngine(s, N=N, water_frac=0.5)  # noqa: E731  (settles → micelles)
        knobs = _KNOBS_ROD
        label = "lipid_rod.py (rigid rod lipids — conservative, settles into micelles)"
    else:
        N = a.N if a.N is not None else 76
        make_engine = lambda s: ChargedEngine(s, N=N, water_frac=0.5)  # noqa: E731  (charge from shape)
        knobs = _KNOBS_CHARGED
        label = "charged.py (neg-centre/pos-lobe tokens + water — polarity from shape, conservative)"
    server = ThreadingHTTPServer((a.host, a.port), Handler)
    server.sim = Sim(a.seed, a.hz, a.steps_per_frame, make_engine, knobs)
    print(f"serving: {label}\nmembrane viewer on http://{a.host}:{server.server_address[1]}\n"
          f"expose on your tailnet:  tailscale serve --bg {server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.sim._stop = True
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
