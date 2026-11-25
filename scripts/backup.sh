#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTANCE="$(realpath "$1")"
if [[ "${2:-}" != "--resume" ]]; then DEST="$(realpath "$2")"; else DEST=""; fi
[[ -f "$INSTANCE/.env" ]] || exit 1
umask 077
PROJECT="$(sed -n 's/^COMPOSE_PROJECT_NAME=//p' "$INSTANCE/.env")"
[[ "$PROJECT" =~ ^jobbi-[a-z0-9-]+$ ]] || exit 1
# Serialize direct and scheduled backups before inspecting or stopping services.
exec {backup_lock}>"$INSTANCE/.backup.lock"
flock -n "$backup_lock" || { echo 'Backup already running for this instance' >&2; exit 1; }
ctl(){ bash "$ROOT/scripts/ctl.sh" "$INSTANCE" "$@"; }
JOURNAL="$INSTANCE/.backup-running-services"
resume_services(){
  local -a services
  mapfile -t services < "$JOURNAL"
  (( ${#services[@]} )) || return 1
  for service in "${services[@]}"; do [[ "$service" =~ ^[a-z0-9][a-z0-9-]*$ ]] || return 1; done
  ctl start "${services[@]}" && rm -- "$JOURNAL"
}
if [[ "${2:-}" == "--resume" ]]; then
  [[ -f "$JOURNAL" ]] || { echo 'No interrupted backup to resume'; exit 0; }
  resume_services
  exit
fi
[[ ! -e "$INSTANCE/.upgrade-hold.json" ]] || { echo "Upgrade hold active; do not back up or restart original until reconciled" >&2; exit 1; }
[[ ! -e "$JOURNAL" ]] || { echo 'Interrupted backup. Inspect the instance, then run backup.sh INSTANCE --resume.' >&2; exit 1; }
[[ -d "$DEST" && "$DEST" != "$INSTANCE" && "$DEST" != "$INSTANCE/"* && "$INSTANCE" != "$DEST/"* ]] || { echo 'Separate backup directory required'; exit 1; }
OUT="$DEST/$PROJECT-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$OUT"
# Preserve the actual running/stopped image identities, not merely mutable tags.
python3 "$ROOT/scripts/release-inventory.py" "$INSTANCE" --record >/dev/null
# Capture non-pullable image IDs before interrupting customer services. Registry
# images are referenced by immutable digest in the backed-up inventory.
image_file=local-images.tar.gz
image_options=()
hold=false
if [[ "${3:-}" == "--hold-for-upgrade" ]]; then
  hold=true
  image_file=all-images.tar.gz
  image_options=(--all-images)
elif [[ "${3:-}" == "--all-images" ]]; then
  image_file=all-images.tar.gz
  image_options=(--all-images)
elif [[ $# -ne 2 ]]; then
  echo 'Usage: backup.sh INSTANCE DEST [--all-images|--hold-for-upgrade]' >&2; exit 2
fi
IMAGE_LIST="$(python3 "$ROOT/scripts/recovery_images.py" "$INSTANCE/image-inventory.json" "${image_options[@]}")"
if [[ -n "$IMAGE_LIST" ]]; then
  mapfile -t LOCAL_IMAGES <<< "$IMAGE_LIST"
  docker image save "${LOCAL_IMAGES[@]}" | gzip -1 > "$OUT/$image_file"
fi
SERVICES="$(ctl ps --status running --services)"
mapfile -t RUNNING <<< "$SERVICES"
[[ -n "$SERVICES" ]] || { echo 'No running services'; exit 1; }
(( ${#RUNNING[@]} )) || { echo "No running services"; exit 1; }
restart_on_exit(){
  local status=$?
  trap - EXIT
  if [[ -e "$JOURNAL" ]] && ! resume_services; then
    echo 'Restart failed; inspect instance immediately' >&2
    exit 1
  fi
  exit "$status"
}
printf '%s\n' "${RUNNING[@]}" > "$JOURNAL.tmp"
mv "$JOURNAL.tmp" "$JOURNAL"
trap restart_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
ctl stop "${RUNNING[@]}"
docker run --rm --network none -v "$INSTANCE:/src:ro" -v "$OUT:/backup:rw" alpine:3.22@sha256:49340b346798875b5592e5d420241f2f9cfba5f47e62ebb1446a1b34734e898f sh -c 'cd /src; set -- .env dashboard.json data; for p in release.json deployment onboarding.json image-inventory.json; do if test -e "$p"; then set -- "$@" "$p"; fi; done; tar czf /backup/instance.tar.gz "$@"'
VOLUMES="$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT")"
while IFS= read -r volume; do
  [[ -n "$volume" ]] || continue
  [[ "$volume" == "$PROJECT"_* ]] || { echo "Unexpected volume"; exit 1; }
  docker run --rm --network none -v "$volume:/src:ro" -v "$OUT:/backup:rw" alpine:3.22@sha256:49340b346798875b5592e5d420241f2f9cfba5f47e62ebb1446a1b34734e898f sh -c 'tar czf "/backup/$1.tar.gz" -C /src .' sh "$volume"
done <<< "$VOLUMES"
(cd "$OUT" && sha256sum ./*.tar.gz > SHA256SUMS.tmp && sha256sum -c SHA256SUMS.tmp && mv SHA256SUMS.tmp SHA256SUMS)
if $hold; then
  # Record the exact originally running services and completed archive. Keep
  # the normal interrupted-backup journal until the hold is safely recorded.
  python3 - "$INSTANCE" "$OUT" <<'PY'
import json,os,sys
from pathlib import Path
i=Path(sys.argv[1]);b=Path(sys.argv[2]);journal=i/'.backup-running-services'
p=i/'.upgrade-hold.json';tmp=i/'.upgrade-hold.tmp'
with tmp.open('x') as out:
    json.dump({'state':'held','backup':str(b),'services':journal.read_text().splitlines()},out)
    out.flush();os.fsync(out.fileno())
os.replace(tmp,p)
PY
  rm -- "$JOURNAL"
else
  resume_services
fi
echo "Backup: $OUT (contains secrets; encrypt and test restoration on separate host)"
