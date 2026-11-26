#!/usr/bin/env bash
# Dedicated quote preview; does not read the production quote .env.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
# An explicit env file prevents automatic .env loading. Explicit variables and
# project name keep the production listener and containers untouched.
export QUOTE_BIND=127.0.0.1 QUOTE_PORT=8781
compose=(docker compose --env-file /dev/null --project-name jobbi-quote-preview -f "$ROOT/compose.yaml")
case "${1:-up}" in
  up)
    "${compose[@]}" up -d --build
    "${compose[@]}" ps
    for attempt in $(seq 1 20); do
      if curl --noproxy '*' --max-time 3 -fsS http://127.0.0.1:8781/ >/dev/null; then
        echo 'Quote preview ready: http://127.0.0.1:8781 (local backend)'
        echo 'Tailscale Serve must already forward port 8781 to this address.'
        exit 0
      fi
      sleep 1
    done
    "${compose[@]}" logs --tail=30 quote
    echo 'Quote backend not ready; inspect the preview container.' >&2
    exit 1
    ;;
  status) "${compose[@]}" ps; curl --noproxy '*' -fsSI --max-time 5 http://127.0.0.1:8781/ ;;
  logs) "${compose[@]}" logs --tail=50 quote ;;
  stop) "${compose[@]}" stop quote ;;
  *) echo 'Usage: bash quote/preview.sh [up|status|logs|stop]' >&2; exit 2 ;;
esac
