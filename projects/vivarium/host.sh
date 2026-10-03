#!/usr/bin/env bash
# Install/update the active 2-D dish; keep the existing viewer and unrelated Tailscale routes.
set -euo pipefail
vivarium_workspace=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd -- "$vivarium_workspace"
bazel build //projects/vivarium:serve
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/vivarium.service" <<EOF
[Unit]
Description=Vivarium active 2-D molecular dish

[Service]
WorkingDirectory=$vivarium_workspace
# 1000 is deliberately above the measured compute ceiling (~500 steps/s): the loop therefore runs
# as fast as this host permits while still yielding each iteration for control/stream threads.
ExecStart="$vivarium_workspace/bazel-bin/projects/vivarium/serve" --vesicle --vesicle-start dispersed --hz 1000 --autopause 1000000 --port 8090
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable vivarium.service
systemctl --user restart vivarium.service
curl --fail --silent --retry 10 --retry-connrefused --retry-delay 1 --max-time 5 \
    http://127.0.0.1:8090/state > /dev/null
# Serve/Funnel scope belongs to the whole HTTPS listener, not to an individual path.
vivarium_publish=(tailscale serve)
if tailscale serve status --json | python3 -c 'import json,sys; c=json.load(sys.stdin); sys.exit(0 if any(k.endswith(":443") and v for k,v in c.get("AllowFunnel",{}).items()) else 1)'; then
    vivarium_publish=(tailscale funnel)
fi
"${vivarium_publish[@]}" --bg --yes --set-path /vivarium http://127.0.0.1:8090
"${vivarium_publish[@]}" --bg --yes --set-path /vivarium/2d http://127.0.0.1:8090
# The archived 3-D address redirects to /vivarium, rather than proxying a dead port.
"${vivarium_publish[@]}" --bg --yes --set-path /vivarium/3d http://127.0.0.1:8090/vivarium/3d
systemctl --user --no-pager status vivarium.service
