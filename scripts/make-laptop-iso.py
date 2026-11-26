#!/usr/bin/env python3
"""Build a reusable, no-secret connected laptop pilot ISO; does not flash devices."""
import argparse,hashlib,importlib.util,json,re,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('usb',ROOT/'scripts/make-install-usb.py');usb=importlib.util.module_from_spec(spec);spec.loader.exec_module(usb)
def config(commit):
    if not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('Exact reviewed commit required')
    boot="""#!/bin/bash
set -euo pipefail
umask 022
root=/opt/jobbi-aio
test ! -e "$root" || test -d "$root/.git"
if [[ ! -d "$root/.git" ]]; then
 git init "$root"
 git -C "$root" remote add origin https://github.com/b3njaram/AIO.git
fi
test "$(git -C "$root" remote get-url origin)" = https://github.com/b3njaram/AIO.git
if ! git -C "$root" rev-parse --verify HEAD >/dev/null 2>&1; then
 git -C "$root" fetch --depth 1 origin """+commit+"""
 git -C "$root" checkout --detach FETCH_HEAD
fi
test "$(git -C "$root" rev-parse HEAD)" = """+commit+"""
exec python3 "$root/scripts/laptop-first-boot.py"
"""
    unit='[Unit]\nDescription=Jobbi connected laptop first boot\nWants=network-online.target\nAfter=network-online.target docker.service cloud-final.service\nRequires=docker.service\nConditionPathExists=!/var/lib/jobbi/pilot-provisioned\n[Service]\nType=oneshot\nExecStart=/usr/local/sbin/jobbi-laptop-first-boot\nTimeoutStartSec=infinity\nUMask=0077\n[Install]\nWantedBy=multi-user.target\n'
    def f(path,content,permissions='0644'):return dict(path=path,content=content,permissions=permissions,owner='root:root')
    return {'autoinstall':{'version':1,'interactive-sections':['storage','identity'],'ssh':{'install-server':False,'allow-pw':False},'packages':['docker.io','docker-compose-v2','git','python3','curl','smartmontools','util-linux','python3-socketio','python3-websocket','mdadm','age','lvm2','openssl','nginx'],'late-commands':['curtin in-target -- systemctl mask nginx.service'],'user-data':{'write_files':[f('/etc/jobbi/pilot-revision',commit+'\n'),f('/usr/local/sbin/jobbi-laptop-first-boot',boot,'0700'),f('/etc/systemd/system/jobbi-laptop-first-boot.service',unit)],'runcmd':[['systemctl','daemon-reload'],['systemctl','enable','--now','docker'],['systemctl','enable','jobbi-laptop-first-boot.service'],['systemctl','start','--no-block','jobbi-laptop-first-boot.service']]}}}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ubuntu-iso',type=Path,required=True);p.add_argument('--iso-sha256',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.ubuntu_iso.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=a.iso_sha256.lower():p.error('Verified official ISO checksum mismatch')
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip():p.error('Use clean committed checkout')
    a.out=a.out.expanduser().resolve()
    if a.out.exists() or a.out==ROOT or ROOT in a.out.parents:p.error('Use new output directory outside Git')
    a.out.mkdir(mode=0o700,parents=True)
    seed=a.out/'autoinstall.yaml';seed.write_text(json.dumps(config(commit),indent=2)+'\n')
    output=a.out/'jobbi-laptop.iso';usb.remaster_iso(a.ubuntu_iso,seed,output)
    with output.open('rb') as stream:checksum=hashlib.file_digest(stream,'sha256').hexdigest()
    (a.out/'SHA256SUMS').write_text(checksum+'  '+output.name+'\n')
    print('Pilot ISO created:',output,'; verify checksum, boot only isolated lab, select SSD and guided LVM, choose jobbi operator.')
if __name__=='__main__':main()
