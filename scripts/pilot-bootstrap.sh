#!/usr/bin/env bash
# Dedicated physical pilot only. Existing mode changes dashboard and host health units only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[[ $(id -u) != 0 ]] || { echo 'Run as the original non-root appliance operator'; exit 1; }
MODE=""; APPLY=0; CREATE=0; VG=ubuntu-vg; SIZE=300G; NAME=laptop-test; DATA=/srv/jobbi-data; BACKUP=""; SMART=""; OWNER=owner
while [[ $# -gt 0 ]]; do
 case "$1" in
  --existing|--fresh) [[ -z "$MODE" ]] || exit 2; MODE="$1"; shift;;
  --apply) APPLY=1; shift;;
  --create-data-lv) CREATE=1; shift;;
  --vg) VG="$2"; shift 2;;
  --size) SIZE="$2"; shift 2;;
  --name) NAME="$2"; shift 2;;
  --backup-root) BACKUP="$2"; shift 2;;
  --smart-device) SMART="$2"; shift 2;;
  --username) OWNER="$2"; shift 2;;
  *) echo "Unknown option: $1"; exit 2;;
 esac
done
[[ "$MODE" && "$NAME" =~ ^[a-z0-9][a-z0-9-]{0,35}$ && "$VG" =~ ^[A-Za-z0-9_-]+$ && "$SIZE" =~ ^[1-9][0-9]*G$ && "$OWNER" =~ ^[A-Za-z0-9_.-]{1,48}$ ]] || { echo 'Choose --fresh or --existing and safe names'; exit 2; }
[[ -z "$SMART" || "$SMART" =~ ^/dev/(sd[a-z]+|nvme[0-9]+n[0-9]+|disk/by-id/[A-Za-z0-9_.:+-]+)$ ]] || exit 2
source /etc/os-release
[[ "$ID" == ubuntu && ( "$VERSION_ID" == 24.04 || "$VERSION_ID" == 26.04 ) && $(uname -m) == x86_64 ]] || { echo 'Requires Ubuntu 24.04 or experimental 26.04 x86-64'; exit 1; }
INSTANCE="$DATA/$NAME"; LV="/dev/$VG/jobbi-data"; REV="$(git rev-parse HEAD)"
echo "Mode $MODE; instance $INSTANCE; data LV $LV; release $REV"
echo "Backup: ${BACKUP:-not configured}; SMART: ${SMART:-not selected}; create LV: $CREATE"
[[ "$APPLY" == 1 ]] || { echo 'Preview only; append --apply after checking the dedicated test host'; exit 0; }
[[ -z "$(git status --porcelain)" ]] || { echo 'Use a clean reviewed checkout'; exit 1; }
if [[ "$MODE" == --fresh ]]; then
 [[ ! -e "$INSTANCE" ]] || { echo 'Instance exists; use --existing'; exit 1; }
 if ! mountpoint -q "$DATA"; then
  if [[ ! -b "$LV" ]]; then
   [[ "$CREATE" == 1 ]] || { echo 'Mount approved data filesystem first, or explicitly request --create-data-lv'; exit 1; }
   echo "Creates a NEW $SIZE logical volume $LV. Existing volumes are not formatted."
   read -r -p "Type CREATE to proceed: " answer
   [[ "$answer" == CREATE ]] || exit 1
   sudo lvcreate -L "$SIZE" -n jobbi-data "$VG"
   sudo mkfs.ext4 -L jobbi-data "$LV"
  fi
  [[ $(sudo blkid -s TYPE -o value "$LV") == ext4 ]] || { echo 'Existing LV is not ext4; inspect manually'; exit 1; }
  sudo mkdir -p "$DATA"
  [[ -z "$(ls -A "$DATA")" ]] || { echo 'Unmounted data directory is not empty'; exit 1; }
  sudo mount "$LV" "$DATA"
 fi
 uuid="$(findmnt -n -o UUID --mountpoint "$DATA")"
 [[ "$uuid" =~ ^[A-Fa-f0-9-]+$ ]] || exit 1
 existing="$(findmnt --fstab -n -o UUID --mountpoint "$DATA" || true)"
 if [[ -z "$existing" ]]; then
  printf 'UUID=%s %s ext4 defaults 0 2\n' "$uuid" "$DATA" | sudo tee -a /etc/fstab >/dev/null
 elif [[ "$existing" != "$uuid" ]]; then echo 'Existing fstab entry differs'; exit 1; fi
 sudo systemctl daemon-reload
 sudo findmnt --verify
 sudo chown "$(id -u):$(id -g)" "$DATA"
 sudo apt-get update
 sudo apt-get install -y docker.io docker-compose-v2 python3 git curl util-linux smartmontools python3-socketio python3-websocket mdadm age
 if apt-cache show docker-buildx >/dev/null 2>&1; then sudo apt-get install -y docker-buildx; fi
 sudo systemctl enable --now docker
 if ! docker info >/dev/null 2>&1; then
  sudo usermod -aG docker "$USER"
  echo 'Docker access granted (root-equivalent). Log out/in, then rerun the same command. Existing data is preserved.'
  exit 1
 fi
 [[ -z "$(docker ps -aq)" ]] || { echo 'Fresh install requires dedicated empty Docker host'; exit 1; }
 sudo python3 scripts/boot-guard.py "$DATA" --apply
 pre=(--data-root "$DATA" --apps music,movies,photos,files,passwords,tasks,monitor)
 [[ -z "$BACKUP" ]] || pre+=(--backup-root "$BACKUP")
 python3 scripts/preflight.py "${pre[@]}"
 python3 scripts/install.py --name "$NAME" --data-root "$DATA" --base-port 18080 --bind 127.0.0.1 --music-admin "$OWNER" --apps music,movies,photos,files,passwords,tasks,monitor
else
 python3 scripts/pilot-dashboard-update.py "$INSTANCE"
fi
# SMART is optional and requires a root-owned, pinned code checkout. No root timer executes operator-writable scripts.
HEALTH_ROOT="$ROOT"
if [[ -n "$SMART" ]]; then
 [[ -b "$SMART" ]] || { echo 'Selected SMART device missing'; exit 1; }
 HEALTH_ROOT="/opt/jobbi-pilot-health-$REV"
 if [[ ! -e "$HEALTH_ROOT" ]]; then
  sudo git clone --no-checkout https://github.com/b3njaram/AIO.git "$HEALTH_ROOT"
  sudo git -C "$HEALTH_ROOT" checkout --detach "$REV"
 fi
 [[ "$(sudo git -C "$HEALTH_ROOT" rev-parse HEAD)" == "$REV" && -z "$(sudo git -C "$HEALTH_ROOT" status --porcelain)" && "$(stat -c %u "$HEALTH_ROOT")" == 0 ]] || { echo 'Root-owned checkout mismatch'; exit 1; }
fi
health=("$INSTANCE" --operator "$USER" --check-updates --apply)
if [[ -n "$BACKUP" ]]; then health=("$INSTANCE" "$BACKUP" --operator "$USER" --check-updates --apply); else health+=(--no-backup); fi
[[ -z "$SMART" ]] || health+=(--smart-device "$SMART")
sudo python3 "$HEALTH_ROOT/scripts/install-health-service.py" "${health[@]}"
bash scripts/verify.sh "$INSTANCE"
echo 'Dashboard: http://127.0.0.1:18080/ (via existing SSH tunnel)'
echo "Account wizard: python3 scripts/setup-web.py $INSTANCE"
