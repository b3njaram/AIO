#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTANCE="$(realpath "$1")"; DEST="$(realpath "$2")"
[[ "$DEST" != "$INSTANCE" && "$DEST" != "$INSTANCE/"* ]] || { echo "Backup outside instance required"; exit 1; }
[[ -d "$DEST" && -f "$INSTANCE/.env" ]] || exit 1
umask 077
PROJECT="$(sed -n 's/^COMPOSE_PROJECT_NAME=//p' "$INSTANCE/.env")"
[[ "$PROJECT" =~ ^jobbi-[a-z0-9-]+$ ]] || exit 1
OUT="$DEST/$PROJECT-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$OUT"
ctl(){ bash "$ROOT/scripts/ctl.sh" "$INSTANCE" "$@"; }
mapfile -t RUNNING < <(ctl ps --status running --services)
(( ${#RUNNING[@]} )) || { echo "No running services"; exit 1; }
trap 'ctl start "${RUNNING[@]}" || echo "Restart failed; inspect instance" >&2' EXIT
ctl stop "${RUNNING[@]}"
docker run --rm -v "$INSTANCE:/src:ro" -v "$OUT:/backup:rw" alpine:3.22 sh -c 'tar czf /backup/instance.tar.gz -C /src .env dashboard.json data'
while IFS= read -r volume; do
  [[ "$volume" == "$PROJECT"_* ]] || { echo "Unexpected volume"; exit 1; }
  docker run --rm -v "$volume:/src:ro" -v "$OUT:/backup:rw" alpine:3.22 sh -c 'tar czf "/backup/$1.tar.gz" -C /src .' sh "$volume"
done < <(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT")
(cd "$OUT" && sha256sum ./*.tar.gz > SHA256SUMS && sha256sum -c SHA256SUMS)
echo "Backup: $OUT (contains secrets; encrypt and test restoration on separate host)"
