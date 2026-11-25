#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTANCE="$(realpath "$1")"; DEST="$(realpath "$2")"
[[ "$DEST" != "$INSTANCE" && "$DEST" != "$INSTANCE/"* ]] || { echo "Backup outside instance required"; exit 1; }
[[ -d "$DEST" && -f "$INSTANCE/.env" ]] || exit 1
umask 077
PROJECT="$(sed -n 's/^COMPOSE_PROJECT_NAME=//p' "$INSTANCE/.env")"
[[ "$PROJECT" =~ ^jobbi-[a-z0-9-]+$ ]] || exit 1
# Serialize direct and scheduled backups before inspecting or stopping services.
exec {backup_lock}>"$INSTANCE/.backup.lock"
flock -n "$backup_lock" || { echo 'Backup already running for this instance' >&2; exit 1; }
OUT="$DEST/$PROJECT-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$OUT"
# Preserve the actual running/stopped image identities, not merely mutable tags.
python3 "$ROOT/scripts/release-inventory.py" "$INSTANCE" --record >/dev/null
# Capture non-pullable image IDs before interrupting customer services. Registry
# images are referenced by immutable digest in the backed-up inventory.
IMAGE_LIST="$(python3 "$ROOT/scripts/recovery_images.py" "$INSTANCE/image-inventory.json")"
if [[ -n "$IMAGE_LIST" ]]; then
  mapfile -t LOCAL_IMAGES <<< "$IMAGE_LIST"
  docker image save "${LOCAL_IMAGES[@]}" | gzip -1 > "$OUT/local-images.tar.gz"
fi
ctl(){ bash "$ROOT/scripts/ctl.sh" "$INSTANCE" "$@"; }
SERVICES="$(ctl ps --status running --services)"
mapfile -t RUNNING <<< "$SERVICES"
[[ -n "$SERVICES" ]] || { echo 'No running services'; exit 1; }
(( ${#RUNNING[@]} )) || { echo "No running services"; exit 1; }
restart_on_exit(){
  local status=$?
  trap - EXIT
  if ! ctl start "${RUNNING[@]}"; then
    echo 'Restart failed; inspect instance immediately' >&2
    exit 1
  fi
  exit "$status"
}
trap restart_on_exit EXIT
ctl stop "${RUNNING[@]}"
docker run --rm --network none -v "$INSTANCE:/src:ro" -v "$OUT:/backup:rw" alpine:3.22 sh -c 'cd /src; set -- .env dashboard.json data; for p in release.json deployment onboarding.json image-inventory.json; do if test -e "$p"; then set -- "$@" "$p"; fi; done; tar czf /backup/instance.tar.gz "$@"'
VOLUMES="$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT")"
while IFS= read -r volume; do
  [[ -n "$volume" ]] || continue
  [[ "$volume" == "$PROJECT"_* ]] || { echo "Unexpected volume"; exit 1; }
  docker run --rm --network none -v "$volume:/src:ro" -v "$OUT:/backup:rw" alpine:3.22 sh -c 'tar czf "/backup/$1.tar.gz" -C /src .' sh "$volume"
done <<< "$VOLUMES"
(cd "$OUT" && sha256sum ./*.tar.gz > SHA256SUMS.tmp && sha256sum -c SHA256SUMS.tmp && mv SHA256SUMS.tmp SHA256SUMS)
echo "Backup: $OUT (contains secrets; encrypt and test restoration on separate host)"
