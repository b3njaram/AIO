#!/usr/bin/env bash
# ONLY disposable GitHub-hosted runner. All member disks are fresh loop images.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${RUNNER_ENVIRONMENT:-}" == github-hosted && $EUID == 0 ]] || { echo 'Disposable hosted CI only'; exit 1; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d /tmp/jobbi-raid-pilot.XXXXXXXX)"
array="/dev/md/jobbi-pilot-${GITHUB_RUN_ID:?}-${GITHUB_RUN_ATTEMPT:?}"
[[ ! -e "$array" && ! -L "$array" ]] || exit 1
loops=()
created=false
cleanup(){
  if mountpoint -q "$WORK/mount"; then umount "$WORK/mount"; fi
  if $created; then mdadm --stop "$array" || true; fi
  for loop in "${loops[@]}"; do losetup -d "$loop" || true; done
  rm -rf -- "$WORK"
}
trap cleanup EXIT
mkdir "$WORK/mount"
for n in a b c d; do
  size=128M
  [[ "$n" == c || "$n" == d ]] && size=256M
  truncate -s "$size" "$WORK/$n.img"
  loop="$(losetup --find --show "$WORK/$n.img")"
  [[ "$loop" =~ ^/dev/loop[0-9]+$ ]] || exit 1
  [[ "$(losetup --noheadings --output BACK-FILE "$loop" | xargs)" == "$WORK/$n.img" ]] || exit 1
  loops+=("$loop")
done
[[ "$(printf '%s\n' "${loops[@]}" | sort -u | wc -l)" == 4 ]] || exit 1
mdadm --create "$array" --metadata=1.2 --level=1 --raid-devices=2 --size=65536 --run "${loops[0]}" "${loops[1]}"
created=true
dev="$(realpath "$array")"
[[ "$dev" =~ ^/dev/md[0-9]+$ ]] || exit 1
wait_idle(){
  for n in $(seq 1 180); do
    if [[ "$(cat "/sys/class/block/${dev##*/}/md/sync_action")" == idle && "$(cat "/sys/class/block/${dev##*/}/md/degraded")" == 0 ]]; then return 0; fi
    sleep 1
  done
  cat /proc/mdstat; return 1
}
wait_idle
mkfs.ext4 -q "$dev"
mount "$dev" "$WORK/mount"
dd if=/dev/urandom of="$WORK/mount/fixture" bs=1M count=2 status=none
expected="$(sha256sum "$WORK/mount/fixture" | cut -d' ' -f1)"
uuid="$(blkid -s UUID -o value "$dev")"
before="$(df -B1 --output=size "$WORK/mount" | tail -1 | xargs)"
for n in 0 1; do
  mdadm "$array" --fail "${loops[$n]}"
  mdadm "$array" --remove "${loops[$n]}"
  PYTHONPATH="$ROOT/scripts" python3 - "$dev" "${loops[$((n+2))]}" <<'PY'
import sys,subprocess
from storage_manager import read_md,replacement
md=read_md(sys.argv[1]);assert md['degraded']==1
replacement(md,{'size':int(subprocess.check_output(['blockdev','--getsize64',sys.argv[2]]))})
PY
  test "$(sha256sum "$WORK/mount/fixture" | cut -d' ' -f1)" = "$expected"
  mdadm "$array" --add "${loops[$((n+2))]}"
  wait_idle
done
PYTHONPATH="$ROOT/scripts" python3 - "$dev" <<'PY'
import sys,subprocess
from storage_manager import read_md,expansion
m=read_md(sys.argv[1]);nodes={x['device']:{'size':int(subprocess.check_output(['blockdev','--getsize64',x['device']]))} for x in m['members']}
assert expansion(m,nodes,'ext4')>m['component_bytes']
PY
umount "$WORK/mount"
mdadm "$array" --grow --size=max
wait_idle
e2fsck -f -p "$dev"
resize2fs "$dev"
mount "$dev" "$WORK/mount"
after="$(df -B1 --output=size "$WORK/mount" | tail -1 | xargs)"
test "$after" -gt "$before"
test "$(blkid -s UUID -o value "$dev")" = "$uuid"
test "$(sha256sum "$WORK/mount/fixture" | cut -d' ' -f1)" = "$expected"
echo 'PASS: disposable RAID1 degraded read, two replacements, resynchronization, ext4 expansion, same UUID and byte-identical fixture'
