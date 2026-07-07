# thermolife · sim — web control for the fold viewer

The `sim/` package drives the embedding fold (`fold/FoldEngine`) and exposes a **web
control endpoint** to start / pause / restart / stop it and watch the blobs fold and
dock live. Dependency-light: stdlib `http.server` + a client-side `<canvas>` viewer.

## Run it

```bash
# web control server (binds loopback by default)
bazel run //projects/thermolife:serve -- --port 8787
# → http://127.0.0.1:8787
```

Control surface:

| Method | Path | Effect |
|---|---|---|
| GET  | `/`        | the canvas viewer (morphing blobs + docking edges) |
| GET  | `/state`   | JSON snapshot: `status`, `tick`, `fold`, `fold_iter`, `fold_step`, `max_attn`, `tokens` (each `{pos, contour}`), `edges` (`[i,j,weight]`) |
| POST | `/start`   | build a fresh fold (optional `{"seed": N}`) and run |
| POST | `/pause`   | pause stepping (409 if not RUNNING) |
| POST | `/resume`  | resume (409 if not PAUSED) |
| POST | `/restart` | reset to the same seed and run |
| POST | `/stop`    | back to IDLE |

Stepping runs on a single background thread; HTTP handlers only call controller
methods and never touch the engine, so pause/resume timing cannot perturb the
trajectory (determinism, J2).

## Expose it over Tailscale

The app binds to `127.0.0.1`; **Tailscale proxies** it (no Tailscale code in the app).
`sim/host.sh` wraps this; or manually:

```bash
tailscale serve --bg 8787          # private to your tailnet (recommended)
tailscale serve status             # shows the https://<machine>.<tailnet>.ts.net URL
tailscale serve --https=443 off    # off
```

For a **public** URL (opt-in): `tailscale funnel --bg 8787`.

> **Security note.** The control API is **unauthenticated by design** — access control
> is delegated to the tailnet. `serve` keeps it private to your devices; `funnel`
> exposes an unauthenticated start/pause/restart endpoint to the public internet —
> only enable it deliberately.

## Files

- `controller.py` — `SimController`: background thread + `IDLE/RUNNING/PAUSED` state
  machine around any engine (`step`/`tick`/`residual`/`snapshot`).
- `server.py` — stdlib HTTP server; routes control POSTs + `/state` + the viewer.
- `viewer.html` — self-contained canvas page (polls `/state` at ~7 Hz), draws each
  token's contour blob + attention bonds, autoscaled to frame the fold.
- `host.sh` — build + run + Tailscale hosting helper.
