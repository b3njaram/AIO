#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTANCE="$(realpath "$1")"; shift
test -f "$INSTANCE/.env" || { echo "Instance .env not found" >&2; exit 1; }
PROJECT="$(sed -n 's/^COMPOSE_PROJECT_NAME=//p' "$INSTANCE/.env")"
[[ "$PROJECT" =~ ^jobbi-[a-z0-9-]+$ ]] || { echo "Invalid project" >&2; exit 1; }
[[ "$(sed -n 's/^INSTANCE_DIR=//p' "$INSTANCE/.env")" == "$INSTANCE" ]] || { echo "Instance path mismatch" >&2; exit 1; }
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
if [[ -f "$INSTANCE/deployment/recovery-images.json" ]]; then
  FILES+=(-f "$INSTANCE/deployment/recovery-images.json")
fi
exec docker compose --env-file "$INSTANCE/.env" -p "$PROJECT" "${FILES[@]}" "$@"
