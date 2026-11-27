#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTANCE="$(realpath "$1")"; shift
test -f "$INSTANCE/.env" || { echo "Instance .env not found" >&2; exit 1; }
PROJECT="$(sed -n 's/^COMPOSE_PROJECT_NAME=//p' "$INSTANCE/.env")"
[[ "$PROJECT" =~ ^jobbi-[a-z0-9-]+$ ]] || { echo "Invalid project" >&2; exit 1; }
[[ "$(sed -n 's/^INSTANCE_DIR=//p' "$INSTANCE/.env")" == "$INSTANCE" ]] || { echo "Instance path mismatch" >&2; exit 1; }
# The held source is not an ordinary running appliance. Read/stop/cleanup
# remain available, but normal start or recreation is blocked. This is an
# operator safety guard, not a security boundary against Docker administrators.
if [[ -e "$INSTANCE/.upgrade-hold.json" ]]; then
  case "${1:-}" in
    ps|config|logs|images|stop) ;;
    --resume-held)
      shift
      [[ "${1:-}" == start && $# -gt 1 ]] || { echo 'Explicit held-source recovery requires the original service set' >&2; exit 1; }
      python3 - "$INSTANCE" "${@:2}" <<'PY'
import json,sys
from pathlib import Path
i=Path(sys.argv[1]);h=json.loads((i/'.upgrade-hold.json').read_text())
if h.get('state')!='held' or (i/'.backup-running-services').exists() or sorted(h.get('services',[]))!=sorted(sys.argv[2:]):
    sys.exit('Held source recovery service set or journal mismatch')
PY
      ;;
    *) echo 'Source held for an update; use recovery-center.py rollback after reconciliation' >&2; exit 1 ;;
  esac
fi
# Prevent a shell variable from accidentally overriding the customer configuration.
while IFS= read -r line; do
  key="$(printf '%s' "$line" | cut -d= -f1)"
  if [[ "$key" =~ ^[A-Z_][A-Z0-9_]*$ ]]; then unset "$key"; fi
done < "$INSTANCE/.env"
COMPOSE="$INSTANCE/deployment/compose.yaml"
if [[ ! -f "$COMPOSE" ]]; then
  echo "Legacy pilot: using repository deployment file; freeze it before updating." >&2
  COMPOSE="$ROOT/deploy/compose.yaml"
fi
FILES=(-f "$COMPOSE")
# Explicit opt-in experimental extension, never silently used by exact recovery.
if [[ -f "$INSTANCE/deployment/pilot-media.json" ]]; then
  [[ ! -e "$INSTANCE/deployment/recovery-images.json" ]] || { echo 'Experimental media extension is not exact-recovery qualified' >&2; exit 1; }
  FILES+=(-f "$INSTANCE/deployment/pilot-media.json")
fi
if [[ -f "$INSTANCE/deployment/pilot-network.json" ]]; then
  [[ ! -e "$INSTANCE/deployment/recovery-images.json" ]] || { echo 'Experimental DNS extension is not exact-recovery qualified' >&2; exit 1; }
  FILES+=(-f "$INSTANCE/deployment/pilot-network.json")
fi
if [[ -f "$INSTANCE/deployment/recovery-images.json" ]]; then
  FILES+=(-f "$INSTANCE/deployment/recovery-images.json")
fi
exec docker compose --env-file "$INSTANCE/.env" -p "$PROJECT" "${FILES[@]}" "$@"
