#!/usr/bin/env bash
# Manage only the isolated preview projects, never production services.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
umask 077
export PREVIEW_UID="$(id -u)" PREVIEW_GID="$(id -g)"
[[ "$PREVIEW_UID" != 0 ]] || { echo 'Run as your normal owner account, not root' >&2; exit 1; }
PREVIEW_HOME="$HOME/.jobbi-preview"
export PREVIEW_DATA="$PREVIEW_HOME/.jobbi-no-login-demo"
for dir in "$PREVIEW_HOME" "$PREVIEW_DATA"; do
  [[ ! -L "$dir" ]] || { echo 'Refusing symlinked demo storage' >&2; exit 1; }
  mkdir -p -m 700 "$dir"
  [[ -O "$dir" && "$(stat -c '%a' "$dir")" == 700 ]] || { echo "Demo directory must be owned by you with mode 700: $dir" >&2; exit 1; }
done
compose=(docker compose --env-file /dev/null -p jobbi-admin-preview -f "$ROOT/business/dashboard/compose.preview.yaml")
case "${1:-up}" in
  up)
    bash "$ROOT/quote/preview.sh" up
    "${compose[@]}" up -d --build
    for attempt in $(seq 1 30); do
      if curl --noproxy '*' --max-time 3 -fsS http://127.0.0.1:8791/api/init >/dev/null; then
        echo 'Both previews running in Docker.'
        echo 'http://macmini2012:8791  |  http://macmini2012:8781'
        exit 0
      fi
      sleep 1
    done
    "${compose[@]}" logs --tail=50 dashboard
    exit 1
    ;;
  status)
    bash "$ROOT/quote/preview.sh" status
    "${compose[@]}" ps
    curl --noproxy '*' --max-time 5 -fsS http://127.0.0.1:8791/api/init >/dev/null
    echo 'Admin backend OK'
    ;;
  logs) bash "$ROOT/quote/preview.sh" logs; "${compose[@]}" logs --tail=50 dashboard ;;
  stop) "${compose[@]}" stop dashboard; bash "$ROOT/quote/preview.sh" stop ;;
  *) echo 'Usage: bash scripts/preview.sh [up|status|logs|stop]' >&2; exit 2 ;;
esac
