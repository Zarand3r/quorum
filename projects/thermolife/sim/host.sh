#!/usr/bin/env bash
# Build, run, and Tailscale-host the thermolife Slice-0 web control server.
#
#   ./projects/thermolife/sim/host.sh            # tailnet-private (default, safe)
#   MODE=funnel ./projects/thermolife/sim/host.sh   # public internet (opt-in)
#   ./projects/thermolife/sim/host.sh stop       # tear down server + tailscale mapping
#
# Env knobs: PORT (local, 8787) · TS_PORT (tailscale https port, 8443) ·
# SCENARIO (static_gradient) · MODE (serve|funnel).
#
# The app binds to loopback; Tailscale proxies it. `serve` keeps it private to
# your tailnet; `funnel` exposes an UNAUTHENTICATED control endpoint to the
# public internet — only use funnel deliberately (see sim/README.md §security).
set -euo pipefail

PORT="${PORT:-8787}"
TS_PORT="${TS_PORT:-8443}"
SCENARIO="${SCENARIO:-static_gradient}"
MODE="${MODE:-serve}"
RUN_DIR="${TMPDIR:-/tmp}/thermolife"
PIDFILE="$RUN_DIR/serve.pid"
LOG="$RUN_DIR/serve.log"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
mkdir -p "$RUN_DIR"

stop() {
  echo ">> stopping tailscale ${MODE} on :${TS_PORT}"
  tailscale "$MODE" --https="$TS_PORT" off 2>/dev/null || true
  if [[ -f "$PIDFILE" ]]; then
    kill "$(cat "$PIDFILE")" 2>/dev/null || true
    rm -f "$PIDFILE"
  fi
  echo ">> stopped"
}

if [[ "${1:-}" == "stop" ]]; then stop; exit 0; fi

cd "$REPO_ROOT"

echo ">> building //projects/thermolife:serve"
bazel build //projects/thermolife:serve >/dev/null 2>&1
BIN="$REPO_ROOT/bazel-bin/projects/thermolife/serve"

# Restart cleanly if already running.
if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo ">> restarting existing server"
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
fi

echo ">> starting server on 127.0.0.1:${PORT} (scenario=${SCENARIO})"
nohup "$BIN" --scenario "$SCENARIO" --host 127.0.0.1 --port "$PORT" --step-hz 30 \
  >"$LOG" 2>&1 &
echo $! >"$PIDFILE"

echo ">> waiting for health"
if ! curl -sf --retry 40 --retry-delay 1 --retry-connrefused \
     "http://127.0.0.1:${PORT}/state" >/dev/null; then
  echo "!! server did not become healthy; see $LOG" >&2
  tail -n 20 "$LOG" >&2 || true
  exit 1
fi

echo ">> exposing via tailscale ${MODE} on https :${TS_PORT}"
tailscale "$MODE" --bg --https="$TS_PORT" "$PORT"

DNS="$(tailscale status --json \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['Self']['DNSName'].rstrip('.'))")"
URL="https://${DNS}:${TS_PORT}"

echo
echo "============================================================"
echo " thermolife is hosted:"
echo "   ${URL}"
echo "   mode: ${MODE} ($([[ $MODE == funnel ]] && echo 'PUBLIC internet' || echo 'tailnet-private'))"
echo "   local: http://127.0.0.1:${PORT}   log: ${LOG}"
echo "   open it and click Start / Pause / Restart / Stop"
echo "   tear down: $0 stop"
echo "============================================================"
tailscale "$MODE" status 2>/dev/null | sed 's/^/   /' || true
