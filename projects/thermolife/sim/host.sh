#!/usr/bin/env bash
# Build, run, and host the thermolife Slice-0 web control server on a tailnet.
#
#   ./projects/thermolife/sim/host.sh                 # MODE=existing (default): run on
#                                                     #   the port the existing tailscale
#                                                     #   funnel already proxies (no sudo)
#   MODE=serve  ./projects/thermolife/sim/host.sh     # create a tailnet-private mapping
#   MODE=funnel ./projects/thermolife/sim/host.sh     # create a PUBLIC funnel mapping
#   ./projects/thermolife/sim/host.sh stop            # tear down server (+ mapping)
#
# MODE=existing reuses a `tailscale funnel`/`serve` mapping you already have
# (this box maps https://<host>.ts.net -> 127.0.0.1:8080), so it needs no sudo.
# MODE=serve|funnel run `tailscale` directly and require operator rights
# (`sudo tailscale set --operator=$USER` once) or sudo.
#
# The app binds to loopback; Tailscale proxies it. `funnel` exposes an
# UNAUTHENTICATED control endpoint to the public internet — see sim/README.md.
set -euo pipefail

MODE="${MODE:-existing}"
# Default local port: 8080 for `existing` (matches this box's funnel), else 8787.
if [[ "$MODE" == existing ]]; then PORT="${PORT:-8080}"; else PORT="${PORT:-8787}"; fi
TS_PORT="${TS_PORT:-8443}"
RUN_DIR="${TMPDIR:-/tmp}/thermolife"
PIDFILE="$RUN_DIR/serve.pid"
LOG="$RUN_DIR/serve.log"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
mkdir -p "$RUN_DIR"

stop() {
  if [[ "$MODE" != existing ]]; then
    echo ">> removing tailscale ${MODE} on :${TS_PORT}"
    tailscale "$MODE" --https="$TS_PORT" off 2>/dev/null || true
  fi
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

if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo ">> restarting existing server"
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
fi

TRAINED="${TRAINED:-default}"   # default = committed trained weights; none = untrained S0 fold
TRAINED_ARG=()
if [[ "$TRAINED" == default ]]; then
  TRAINED_ARG=(--trained "$REPO_ROOT/projects/thermolife/configs/trained_fold.npz")
elif [[ "$TRAINED" != none ]]; then
  TRAINED_ARG=(--trained "$TRAINED")
fi
echo ">> starting embedding-folding server on 127.0.0.1:${PORT} (trained=${TRAINED})"
nohup "$BIN" --host 127.0.0.1 --port "$PORT" --step-hz 20 "${TRAINED_ARG[@]}" >"$LOG" 2>&1 &
echo $! >"$PIDFILE"

echo ">> waiting for health"
if ! curl -sf --retry 40 --retry-delay 1 --retry-connrefused \
     "http://127.0.0.1:${PORT}/state" >/dev/null; then
  echo "!! server did not become healthy; see $LOG" >&2
  tail -n 20 "$LOG" >&2 || true
  exit 1
fi

DNS="$(tailscale status --json \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['Self']['DNSName'].rstrip('.'))")"

case "$MODE" in
  existing)
    URL="https://${DNS}"  # reuses the pre-existing 443 funnel -> this port
    ACCESS="reusing existing tailscale funnel (public)"
    ;;
  serve|funnel)
    echo ">> exposing via tailscale ${MODE} on https :${TS_PORT}"
    tailscale "$MODE" --bg --https="$TS_PORT" "$PORT"
    URL="https://${DNS}:${TS_PORT}"
    ACCESS="$([[ $MODE == funnel ]] && echo 'PUBLIC internet' || echo 'tailnet-private')"
    ;;
  *) echo "unknown MODE=$MODE (use existing|serve|funnel)" >&2; exit 2 ;;
esac

echo
echo "============================================================"
echo " thermolife is hosted:"
echo "   ${URL}"
echo "   access: ${ACCESS}"
echo "   local: http://127.0.0.1:${PORT}   log: ${LOG}"
echo "   open it and click Start / Pause / Restart / Stop"
echo "   tear down: $0 stop"
echo "============================================================"
