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

# live knobs — physical laws only (measure-don't-reward: the metric never feeds these)
_KNOBS = ("ga", "gi", "gc", "kappa", "torque", "temp")


class Sim:
    """Steps a MembraneEngine in a background thread; publishes the latest snapshot."""

    def __init__(self, seed: int, hz: float, steps_per_frame: int, cfg: dict) -> None:
        self.seed = seed
        self.hz = hz
        self.stream_hz = min(30.0, hz)
        self.steps_per_frame = steps_per_frame
        self.cfg = cfg
        self.lock = threading.Lock()
        self.engine = MembraneEngine(seed, **cfg)
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
            return {
                "t": e.t,
                "L": e.L,
                "bound": e.pos_bound,
                "pos": [[round(float(x), 3), round(float(y), 3)] for x, y in e.pos],
                "species": [int(s) for s in e.species],
                "orient": [[round(float(x), 3), round(float(y), 3)] for x, y in e.orient],
                "metrics": m,
                "knobs": {k: round(float(getattr(e, k)), 3) for k in _KNOBS if hasattr(e, k)},
            }

    def set_knobs(self, updates: dict) -> None:
        with self.lock:
            for k in _KNOBS:
                if k in updates and hasattr(self.engine, k):
                    try:
                        setattr(self.engine, k, max(0.0, float(updates[k])))
                    except (TypeError, ValueError):
                        pass

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def restart(self, same: bool) -> None:
        with self.lock:
            knobs = {k: getattr(self.engine, k) for k in _KNOBS if hasattr(self.engine, k)}
            self.seed = self.seed if same else self.seed + 1
            self.engine = MembraneEngine(self.seed, **self.cfg)
            for k, v in knobs.items():
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
  <h1>membrane self-assembly</h1>
  <p class="sub">amphiphiles → one-particle-thick band. no dictated bonds; a local anisotropic law.</p>
  <div class="m" id="metrics"></div>
  <div style="margin-top:14px">
   <div class="row"><label>attract</label><input id="ga" type="range" min="0" max="0.8" step="0.01"><span id="ga_v"></span></div>
   <div class="row"><label>inter</label><input id="gi" type="range" min="0" max="4" step="0.1"><span id="gi_v"></span></div>
   <div class="row"><label>cohere</label><input id="gc" type="range" min="0" max="0.08" step="0.005"><span id="gc_v"></span></div>
   <div class="row"><label>rod κ</label><input id="kappa" type="range" min="0" max="8" step="0.5"><span id="kappa_v"></span></div>
   <div class="row"><label>torque</label><input id="torque" type="range" min="0" max="0.6" step="0.02"><span id="torque_v"></span></div>
   <div class="row"><label>temp</label><input id="temp" type="range" min="0" max="0.3" step="0.01"><span id="temp_v"></span></div>
  </div>
  <div style="margin-top:10px">
   <button onclick="post('/pause')">pause</button>
   <button onclick="post('/resume')">resume</button>
   <button onclick="post('/restart')">new seed</button>
   <button onclick="post('/restart?same=1')">replay</button>
  </div>
  <p class="sub" style="margin-top:14px">head = red dot · tail = orange stalk (+o) · water = blue ring.
  temp anneals to 0 over the run; nudge it up to melt & re-anneal.</p>
 </div>
</div>
<script>
const cv=document.getElementById('c'), ctx=cv.getContext('2d'), W=cv.width;
// mounted at / or under a prefix (e.g. /vivarium) — resolve endpoints against the page path so the
// stream/POSTs hit THIS server through the tailscale funnel, not the root proxy.
const BASE = location.pathname.replace(/\/$/, '');
const KN=['ga','gi','gc','kappa','torque','temp']; let dragging=false;
for(const k of KN){const el=document.getElementById(k);
  el.addEventListener('input',()=>{document.getElementById(k+'_v').textContent=(+el.value).toFixed(2);});
  el.addEventListener('mousedown',()=>dragging=true);
  el.addEventListener('change',()=>{dragging=false;
    fetch(BASE+'/set?'+k+'='+el.value,{method:'POST'});});}
function post(p){fetch(BASE+p,{method:'POST'});}
function draw(s){
  ctx.clearRect(0,0,W,W); const B=s.bound, sc=W/(2*B);
  const X=x=>(x+B)*sc, Y=y=>(y+B)*sc;
  // water
  ctx.strokeStyle='rgba(43,108,176,0.5)'; ctx.lineWidth=1;
  for(let i=0;i<s.pos.length;i++){ if(s.species[i]!==0) continue;
    const p=s.pos[i]; ctx.beginPath(); ctx.arc(X(p[0]),Y(p[1]),3,0,7); ctx.stroke(); }
  // lipids: stalk head->tail then head dot
  const stalk=0.5;
  for(let i=0;i<s.pos.length;i++){ if(s.species[i]!==1) continue;
    const p=s.pos[i], o=s.orient[i];
    const cx=X(p[0]),cy=Y(p[1]),tx=X(p[0]+stalk*o[0]),ty=Y(p[1]+stalk*o[1]);
    if(Math.abs(tx-cx)<W/2 && Math.abs(ty-cy)<W/2){
      ctx.strokeStyle='rgba(246,173,85,0.85)'; ctx.lineWidth=2;
      ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(tx,ty); ctx.stroke();
      ctx.fillStyle='#f6ad55'; ctx.beginPath(); ctx.arc(tx,ty,1.7,0,7); ctx.fill(); }
    ctx.fillStyle='#e53e3e'; ctx.beginPath(); ctx.arc(cx,cy,3.4,0,7); ctx.fill(); }
  const m=s.metrics;
  document.getElementById('metrics').innerHTML =
    `t = <b>${s.t}</b><br>director order S = <b>${m.S.toFixed(3)}</b> (→1 aligned)<br>`+
    `side-by-side = <b>${m.side.toFixed(3)}</b><br>sheet aspect = <b>${m.sheetness.toFixed(2)}</b> (≫1 = a band)<br>`+
    `lipid clusters = <b>${m.n_lipid_clusters}</b> (→1 = one membrane)`;
  if(!dragging) for(const k of KN){ const el=document.getElementById(k);
    if(k in s.knobs){ el.value=s.knobs[k]; document.getElementById(k+'_v').textContent=(+s.knobs[k]).toFixed(2);} }
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
    p.add_argument("--steps-per-frame", type=int, default=6,
                   help="engine steps per rendered frame (assembly takes ~14k steps)")
    p.add_argument("--N", type=int, default=96)
    a = p.parse_args(argv)
    cfg = dict(N=a.N)   # engine defaults ARE the showcase config (see membrane.py)
    server = ThreadingHTTPServer((a.host, a.port), Handler)
    server.sim = Sim(a.seed, a.hz, a.steps_per_frame, cfg)
    print(f"membrane viewer on http://{a.host}:{server.server_address[1]}\n"
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
