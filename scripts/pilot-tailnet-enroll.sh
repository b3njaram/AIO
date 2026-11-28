#!/usr/bin/env bash
# Physical customer opt-in. No auth key, owner account, DNS changes, or public Funnel.
set -euo pipefail
[[ $EUID == 0 && -t 0 ]] || { echo 'Use the dedicated appliance console with sudo'; exit 1; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || exit 1
[[ -f /var/lib/jobbi/pilot-provisioned ]] || { echo 'Pilot provisioning required'; exit 1; }
bash "$ROOT/scripts/customer-remote.sh"
state="$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("BackendState","unknown"))')"
[[ "$state" == NeedsLogin || "$state" == NoState || "$state" == Stopped ]] || { echo 'Existing tailnet state retained; no account switch performed'; exit 1; }
echo 'Sign in using YOUR own Tailscale account. This will not change LAN DNS or routes.'
read -r -p 'Type CONNECT to start customer enrollment: ' confirm
[[ "$confirm" == CONNECT ]] || exit 1
tailscale up --accept-dns=false --accept-routes=false --hostname=jobbi-home
echo 'Enrollment requested. Review customer ACLs and HTTPS before enabling private Serve.'
