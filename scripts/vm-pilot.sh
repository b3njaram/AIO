#!/usr/bin/env bash
# Disposable GitHub CI only. No physical disks, no host deployment.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true ]] || { echo 'CI disposable VM only' >&2; exit 1; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
chmod 700 "$WORK"
cd "$WORK"
cleanup(){
  if [[ -f qemu.pid ]]; then kill "$(cat qemu.pid)" 2>/dev/null || true; fi
  if [[ -f serial.log ]]; then tail -100 serial.log; fi
  rm -rf -- "$WORK"
}
trap cleanup EXIT
# Pinned checksum; if the official current build changes, stop for review.
curl --fail --location --retry 3 --max-time 600 \
  https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img -o noble.img
echo '04e8f2461a16a44e78a370284471f29616cdd9baf1893df25807b71f985b6c94  noble.img' | sha256sum -c -
qemu-img create -f qcow2 -F qcow2 -b "$WORK/noble.img" system.qcow2 40G
for file in data backup; do
  truncate -s 64G "$file.img"
  mkfs.ext4 -q -F "$file.img"
done
export DATA_UUID="$(blkid -s UUID -o value data.img)" BACKUP_UUID="$(blkid -s UUID -o value backup.img)"
export TEST_COMMIT="$(git -C "$ROOT" rev-parse HEAD)" TEST_ROOT="$ROOT"
ssh-keygen -q -t ed25519 -N '' -f fixture_key
python3 - <<'PY'
import json,os,sys,importlib.util
from pathlib import Path
from types import SimpleNamespace
root=Path(os.environ['TEST_ROOT']);sys.path.insert(0,str(root/'scripts'))
spec=importlib.util.spec_from_file_location('usb',root/'scripts/make-install-usb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
key=Path('fixture_key.pub').read_text().strip()
a=SimpleNamespace(name='vmhome',operator='jobbi',commit=os.environ['TEST_COMMIT'],data_uuid=os.environ['DATA_UUID'],backup_uuid=os.environ['BACKUP_UUID'],apps='monitor',ssh_key=key,weekly_backup=False)
config=m.config(a,'!')['autoinstall']
# Exercise EXACT installed-system cloud-init payload, not an imitation.
# Ubuntu cloud image bypasses Subiquity disk-selection UI; USB boot remains a separate acceptance test.
data=config['user-data']
data.update({'hostname':'vmhome','package_update':True,'packages':config['packages'],'ssh_pwauth':False,'users':[{'name':'jobbi','groups':['sudo'],'sudo':'ALL=(ALL) NOPASSWD:ALL','shell':'/bin/bash','lock_passwd':True,'ssh_authorized_keys':[key]}]})
Path('user-data').write_text('#cloud-config\n'+json.dumps(data))
Path('meta-data').write_text('instance-id: jobbi-vm-pilot\nlocal-hostname: vmhome\n')
PY
cloud-localds seed.iso user-data meta-data
# KVM when available; software emulation otherwise.
accel=(-accel tcg,thread=multi -cpu max)
if [[ -r /dev/kvm && -w /dev/kvm ]]; then accel=(-accel kvm -cpu host); fi
start(){
  local extra=()
  if [[ "${1:-with-data}" == with-data ]]; then extra=(-drive file=data.img,format=raw,if=virtio); fi
  qemu-system-x86_64 "${accel[@]}" -m 4096 -smp 2 -display none \
    -serial file:serial.log -daemonize -pidfile qemu.pid \
    -drive file=system.qcow2,format=qcow2,if=virtio \
    "${extra[@]}" -drive file=backup.img,format=raw,if=virtio \
    -drive file=seed.iso,format=raw,media=cdrom,readonly=on \
    -nic user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:2222-:22
}
guest(){ ssh -i fixture_key -p 2222 -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$WORK/known_hosts" jobbi@127.0.0.1 "$@"; }
wait_ssh(){
  for _ in $(seq 1 90); do if guest true 2>/dev/null; then return; fi; sleep 5; done
  echo 'VM SSH unavailable' >&2; return 1
}
hard_stop(){
  local pid
  pid="$(cat qemu.pid)"
  kill -KILL "$pid"
  for _ in $(seq 1 20); do if ! kill -0 "$pid" 2>/dev/null; then break; fi; sleep 1; done
  rm -f qemu.pid
  sleep 3
}
start
wait_ssh
for _ in $(seq 1 160); do
  if guest 'sudo test -f /var/lib/jobbi/first-boot-complete'; then break; fi
  sleep 5
done
guest 'sudo test -f /var/lib/jobbi/first-boot-complete || { sudo journalctl -u jobbi-first-boot --no-pager -n 80; exit 1; }'
guest 'curl -fsS http://127.0.0.1:18080/healthz'
guest 'sudo systemctl start jobbi-vmhome-health.service && curl -fsS http://127.0.0.1:18080/api/health | python3 -c "import json,sys; assert json.load(sys.stdin).get(\"at\")"'
guest 'i=/srv/jobbi-data/jobbi-instances/vmhome; printf "%s\n" "vm fixture" > "$i/data/.vm-marker"; printf "%s\n" dashboard > "$i/.backup-running-services"; bash /opt/jobbi-aio/scripts/ctl.sh "$i" stop dashboard; sync'
hard_stop
start
wait_ssh
for _ in $(seq 1 60); do
  if guest 'curl -fsS http://127.0.0.1:18080/healthz && test ! -f /srv/jobbi-data/jobbi-instances/vmhome/.backup-running-services'; then break; fi
  sleep 5
done
guest 'curl -fsS http://127.0.0.1:18080/healthz && grep -qx "vm fixture" /srv/jobbi-data/jobbi-instances/vmhome/data/.vm-marker && test ! -f /srv/jobbi-data/jobbi-instances/vmhome/.backup-running-services'
echo 'PASS: first boot, interrupted backup journal, abrupt VM restart and persistent data'
hard_stop
start without-data
wait_ssh
guest 'timeout 150 sudo systemctl start docker && exit 1 || test "$(systemctl is-active docker)" != active'
guest 'test ! -e /srv/jobbi-data/jobbi-instances/vmhome/data/.vm-marker'
echo 'PASS: missing data disk prevents Docker startup'
hard_stop
start
wait_ssh
for _ in $(seq 1 60); do if guest 'curl -fsS http://127.0.0.1:18080/healthz'; then break; fi; sleep 5; done
guest 'curl -fsS http://127.0.0.1:18080/healthz && grep -qx "vm fixture" /srv/jobbi-data/jobbi-instances/vmhome/data/.vm-marker'
echo 'PASS: data disk reattached, original instance available'
