#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTANCE="$1"; USERNAME="$2"
[[ "$USERNAME" =~ ^[a-zA-Z0-9_.-]{1,48}$ ]] || { echo "Invalid username"; exit 1; }
read -rsp "New StreamHub password (at least 12 characters): " PASSWORD; echo
[[ $(printf '%s' "$PASSWORD" | wc -c) -ge 12 ]] || { echo "Password too short"; exit 1; }
# Upstream CLI accepts the password as an argument; trusted Docker admins can see it temporarily.
bash "$ROOT/scripts/ctl.sh" "$INSTANCE" exec -T backend node create-user.js "$USERNAME" "$PASSWORD"
unset PASSWORD
