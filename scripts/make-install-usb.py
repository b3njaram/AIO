#!/usr/bin/env python3
"""Generate customer-specific Ubuntu autoinstall seed and optionally remaster a verified ISO. Never writes a block device."""
import argparse,getpass,hashlib,json,os,re,shlex,subprocess,sys
from pathlib import Path
from install import DEFAULT,APPS
def validate(a):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,30}',a.name) or not re.fullmatch(r'[a-z_][a-z0-9_-]{0,30}',a.operator):raise ValueError('Invalid host or operator name')
    if a.operator=='root' or not re.fullmatch('[a-f0-9]{40}',a.commit):raise ValueError('Use nonroot operator and reviewed full commit')
    for u in (a.data_uuid,a.backup_uuid):
        if not re.fullmatch(r'[A-Za-z0-9-]{8,80}',u):raise ValueError('Provide existing formatted filesystem UUID')
    if a.data_uuid==a.backup_uuid:raise ValueError('Independent filesystems required')
    apps=list(dict.fromkeys(a.apps.split(',')))
    if not apps or any(x not in set(APPS)-{'dns','navidrome'} for x in apps) or apps==['remote']:raise ValueError('Select core apps; DNS is separate')
    return apps
def mount_unit(uuid,path):
    return '[Unit]\nDescription=Jobbi approved existing filesystem\n[Mount]\nWhat=/dev/disk/by-uuid/'+uuid+'\nWhere='+path+'\nType=auto\nOptions=defaults,nosuid,nodev,nofail\n[Install]\nWantedBy=local-fs.target\n'
def config(a,password_hash):
    apps=validate(a)
    # UUIDs refer to existing volumes; no storage layout or wipe instructions.
    settings={'name':a.name,'operator':a.operator,'commit':a.commit,'data_uuid':a.data_uuid,'backup_uuid':a.backup_uuid,'apps':','.join(apps),'weekly_backup':getattr(a,'weekly_backup',False)}
    # First boot does not rely on a graphical login. Pin checkout before executing.
    boot='''#!/bin/bash
set -euo pipefail
umask 022
ROOT=/opt/jobbi-aio
if [[ ! -d "$ROOT/.git" ]]; then
  test ! -e "$ROOT"
  git init "$ROOT"
  git -C "$ROOT" remote add origin https://github.com/b3njaram/AIO.git
fi
test "$(git -C "$ROOT" remote get-url origin)" = https://github.com/b3njaram/AIO.git
if ! git -C "$ROOT" rev-parse --verify HEAD >/dev/null 2>&1; then
  git -C "$ROOT" fetch --depth 1 origin '''+a.commit+'''
  git -C "$ROOT" checkout --detach FETCH_HEAD
fi
test "$(git -C "$ROOT" rev-parse HEAD)" = '''+a.commit+'''
exec python3 "$ROOT/scripts/first-boot.py" /etc/jobbi/install.json
'''
    service='''[Unit]
Description=JobbiSoft first boot provisioning
Wants=network-online.target
After=network-online.target docker.service srv-jobbi\\\\x2ddata.mount mnt-jobbi\\\\x2dbackup.mount
Requires=docker.service srv-jobbi\\\\x2ddata.mount mnt-jobbi\\\\x2dbackup.mount
ConditionPathExists=!/var/lib/jobbi/first-boot-complete
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/jobbi-first-boot
TimeoutStartSec=infinity
UMask=0077
[Install]
WantedBy=multi-user.target
'''.replace('\\\\','\\')
    def file(path,body,mode='0644'):return {'path':path,'content':body,'permissions':mode,'owner':'root:root'}
    files=[file('/etc/jobbi/install.json',json.dumps(settings,indent=2),'0600'),file('/usr/local/sbin/jobbi-first-boot',boot,'0700'),file('/etc/systemd/system/jobbi-first-boot.service',service),file('/etc/systemd/system/srv-jobbi\\x2ddata.mount',mount_unit(a.data_uuid,'/srv/jobbi-data')),file('/etc/systemd/system/mnt-jobbi\\x2dbackup.mount',mount_unit(a.backup_uuid,'/mnt/jobbi-backup'))]
    # Literal backslash in the escaped mount unit name; JSON serializes safely.
    return {'autoinstall':{'version':1,'interactive-sections':['storage'],'identity':{'hostname':a.name,'username':a.operator,'password':password_hash},'ssh':{'install-server':True,'allow-pw':False,'authorized-keys':[a.ssh_key]},'packages':['docker.io','docker-compose-v2','git','python3','curl','smartmontools','util-linux'],'user-data':{'write_files':files,'runcmd':[['systemctl','daemon-reload'],['systemctl','enable','--now','docker'],['systemctl','enable','srv-jobbi\\x2ddata.mount','mnt-jobbi\\x2dbackup.mount'],['systemctl','enable','jobbi-first-boot.service'],['systemctl','start','--no-block','jobbi-first-boot.service']]}}}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--name',required=True);p.add_argument('--operator',default='jobbi');p.add_argument('--commit',required=True);p.add_argument('--data-uuid',required=True);p.add_argument('--backup-uuid',required=True);p.add_argument('--apps',default=DEFAULT);p.add_argument('--weekly-backup',action='store_true',help='Customer approved weekly cold backup downtime');p.add_argument('--ssh-key-file',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--ubuntu-iso',type=Path);p.add_argument('--iso-sha256');a=p.parse_args()
    validate(a)
    a.ssh_key=a.ssh_key_file.read_text().strip()
    if '\n' in a.ssh_key or not re.fullmatch(r'(?:ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256) [A-Za-z0-9+/=]+(?: [^\r\n]+)?',a.ssh_key):p.error('Use a single authorized public SSH key')
    if a.ubuntu_iso:
        if not a.iso_sha256 or not re.fullmatch('[a-fA-F0-9]{64}',a.iso_sha256) or not a.ubuntu_iso.is_file():p.error('Provide a regular official ISO and verified SHA256')
        with a.ubuntu_iso.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=a.iso_sha256.lower():p.error('ISO checksum mismatch')
    if a.out.exists():p.error('Use a new private output directory')
    pw=getpass.getpass('New local operator password (12+ characters): ')
    if len(pw)<12 or '\n' in pw or pw!=getpass.getpass('Confirm: '):p.error('Password mismatch or too short')
    hashed=subprocess.check_output(['openssl','passwd','-6','-stdin'],input=pw+'\n',text=True).strip();del pw
    os.umask(0o077);a.out.mkdir(mode=0o700)
    cfg=config(a,hashed);raw=json.dumps(cfg,indent=2)+'\n'
    (a.out/'user-data').write_text('#cloud-config\n'+raw)
    (a.out/'meta-data').write_text('instance-id: jobbi-'+a.name+'\nlocal-hostname: '+a.name+'\n')
    (a.out/'autoinstall.yaml').write_text(raw)
    if a.ubuntu_iso:
        output=a.out/'jobbi-ubuntu-server.iso'
        subprocess.run(['xorriso','-indev',str(a.ubuntu_iso),'-outdev',str(output),'-map',str(a.out/'autoinstall.yaml'),'/autoinstall.yaml','-boot_image','any','replay','-commit','-end'],check=True)
        output.chmod(0o600)
    print('Private installer seed created at',a.out)
    print('Review disk selection interactively; do not erase data/backup UUIDs. Never distribute this customer-specific seed or password hash.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.CalledProcessError) as e:sys.exit('USB preparation stopped: '+str(e))
