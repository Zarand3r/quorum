# thermolife · sim — operational loop + web control

The `sim/` package runs the Slice-0 substrate forward and exposes a **web control
endpoint** to start / pause / restart / stop the simulation and watch it live.
It is deliberately dependency-light (stdlib `http.server`; a client-side
`<canvas>` viewer) — see IMPLEMENTATION_PLAN.md §D1–D3.

## Run it

```bash
# headless (no server) — the Slice-0 gate run
bazel run //projects/thermolife:run -- --scenario static_gradient --ticks 6000 --seed 42

# web control server (binds loopback by default)
bazel run //projects/thermolife:serve -- --port 8787
# → http://127.0.0.1:8787
```

Control surface:

| Method | Path | Effect |
|---|---|---|
| GET  | `/`        | the canvas viewer |
| GET  | `/state`   | JSON snapshot: `tick`, `status`, `residual`, `nutrient` grid, `forager`, `alive`, `energy_total` |
| POST | `/start`   | build the world (optional `{"seed": N}`) and run |
| POST | `/pause`   | pause stepping (409 if not RUNNING) |
| POST | `/resume`  | resume (409 if not PAUSED) |
| POST | `/restart` | reset to tick 0 with the same seed and run |
| POST | `/stop`    | back to IDLE |

The stepping runs on a single background thread; HTTP handlers only call
controller methods and never touch the world, so pause/resume timing cannot
perturb the trajectory (determinism, P8).

## Expose it over Tailscale

The app binds to `127.0.0.1`; **Tailscale proxies** it — there is no Tailscale
code in the app. Start the server, then in another shell:

```bash
# private to YOUR tailnet (recommended default): reachable from your own devices
tailscale serve --bg 8787
tailscale serve status            # shows the https://<machine>.<tailnet>.ts.net URL

# turn it off
tailscale serve --https=443 off
```

For a **public** URL on the internet (opt-in — security decision below):

```bash
tailscale funnel --bg 8787        # anyone with the URL can reach it
tailscale funnel status
tailscale funnel --https=443 off
```

> **Security note.** The control API is **unauthenticated by design** — access
> control is delegated to the tailnet. `tailscale serve` keeps it private to your
> devices. `tailscale funnel` exposes an *unauthenticated start/pause/restart
> endpoint to the public internet*; only enable it deliberately, and prefer
> adding auth (or a reverse proxy) first. This is IMPLEMENTATION_PLAN.md §D2.

## Files

- `controller.py` — `SimEngine` (deterministic stepper + snapshot) and
  `SimController` (background thread + `IDLE/RUNNING/PAUSED` state machine).
- `server.py` — stdlib HTTP server; routes control POSTs + `/state` + the viewer.
- `viewer.html` — self-contained canvas page (polls `/state` at ~5 Hz).
- `forager.py` · `tick.py` · `runner.py` — the Slice-0 physics loop.
