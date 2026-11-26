#!/usr/bin/env bash
# GitHub disposable runner only. Does not write physical disks.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true ]] || exit 1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
cd "$WORK"
curl --fail --location --retry 3 --max-time 900 \
  https://releases.ubuntu.com/24.04/ubuntu-24.04.5-live-server-amd64.iso -o ubuntu.iso
echo '97f3d7ffb032c3eb3b23d2c8be9cc76e60c2c1f2c0146ba5ba9fe01cafae0fd8  ubuntu.iso' | sha256sum -c -
export TEST_ROOT="$ROOT" TEST_COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
python3 - <<'PY'
import importlib.util,json,os,sys
from pathlib import Path
from types import SimpleNamespace
root=Path(os.environ['TEST_ROOT']);sys.path.insert(0,str(root/'scripts'))
spec=importlib.util.spec_from_file_location('usb',root/'scripts/make-install-usb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=SimpleNamespace(name='isopilot',operator='jobbi',commit=os.environ['TEST_COMMIT'],data_uuid='11111111-1111-4111-8111-111111111111',backup_uuid='22222222-2222-4222-8222-222222222222',apps='monitor',ssh_key='ssh-ed25519 AAAA fixture-only')
cfg=m.config(a,'!')
Path('autoinstall.yaml').write_text(json.dumps(cfg,indent=2)+'\n')
m.remaster_iso(Path('ubuntu.iso'),Path('autoinstall.yaml'),Path('jobbi.iso'))
PY
xorriso -osirrox on -indev jobbi.iso -extract /autoinstall.yaml extracted.yaml
cmp autoinstall.yaml extracted.yaml
xorriso -indev ubuntu.iso -report_el_torito plain > original-boot.txt 2>&1
xorriso -indev jobbi.iso -report_el_torito plain > new-boot.txt 2>&1
for entry in BIOS UEFI; do
  grep -E "El Torito boot img.*$entry" original-boot.txt
  grep -E "El Torito boot img.*$entry" new-boot.txt
done
python3 - <<'PY'
import json
c=json.load(open('extracted.yaml'))['autoinstall']
assert c['interactive-sections']==['storage']
assert 'storage' not in c and not c['ssh']['allow-pw']
assert any(f['path']=='/etc/systemd/system/jobbi-first-boot.service' for f in c['user-data']['write_files'])
PY
echo 'PASS: official checksum-pinned Ubuntu Server ISO remaster, exact seed, BIOS/UEFI boot catalog and interactive disk selection'
