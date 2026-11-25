#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTANCE="$(realpath "$1")"
ENV="$INSTANCE/.env"
test -f "$ENV"
read_key(){ sed -n "s/^$1=//p" "$ENV"; }
bash "$ROOT/scripts/ctl.sh" "$INSTANCE" config --quiet
bash "$ROOT/scripts/ctl.sh" "$INSTANCE" ps
BASE="http://$(read_key BIND_IP):$(read_key DASH_PORT)"
curl -fsS --retry 10 --retry-all-errors --retry-delay 1 "$BASE/healthz"
curl -fsS --max-time 30 "$BASE/api/status" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps(d,indent=2)); sys.exit(any(a["state"]=="unavailable" for a in d["apps"]))'
echo "HTTP reachability only; complete docs/HANDOFF.md."
