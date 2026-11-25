#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$HOME/.local/share/jobbi-business/sourcing-venv/bin/python"
test -x "$PY" || { echo 'Run business/sourcing/setup-dealcompare.sh first'; exit 1; }
exec "$PY" "$ROOT/business/dashboard/server.py" "$@"
