#!/usr/bin/env python3
"""Generate customer-specific Ubuntu autoinstall seed and optionally remaster a verified ISO. Never writes a block device."""
import argparse,getpass,hashlib,json,os,re,shlex,subprocess,sys
from pathlib import Path
from install import DEFAULT,APPS
ROOT=Path(__file__).resolve().parents[1]
def validate(a):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,30}',a.name) or not re.fullmatch(r'[a-z_][a-z0-9_-]{0,30}',a.operator):raise ValueError('Invalid host or operator name')
    if a.operator=='root' or not re.fullmatch('[a-f0-9]{40}',a.commit):raise ValueError('Use nonroot operator and reviewed full commit')
    for u in (a.data_uuid,a.backup_uuid):
        if not re.fullmatch(r'[A-Za-z0-9-]{8,80}',u):raise ValueError('Provide existing formatted filesystem UUID')
    if a.data_uuid==a.backup_uuid:raise ValueError('Independent filesystems required')
    if not re.fullmatch(r'[A-Za-z0-9_+/-]+',getattr(a,'tz','America/Ciudad_Juarez')):raise ValueError('Invalid timezone')
    if not 1024<=getattr(a,'base_port',18080)<=65525:raise ValueError('Invalid base port')
    apps=list(dict.fromkeys(a.apps.split(',')))
    if not apps or any(x not in set(APPS)-{'dns','navidrome'} for x in apps) or apps==['remote']:raise ValueError('Select core apps; DNS is separate')
    return apps
def mount_unit(uuid,path):
    return '[Unit]\nDescription=Jobbi approved existing filesystem\n[Mount]\nWhat=/dev/disk/by-uuid/'+uuid+'\nWhere='+path+'\nType=auto\nOptions=defaults,nosuid,nodev,nofail\n[Install]\nWantedBy=local-fs.target\n'
def config(a,password_hash):
    apps=validate(a)
    # UUIDs refer to existing volumes; no storage layout or wipe instructions.
    settings={'name':a.name,'operator':a.operator,'commit':a.commit,'data_uuid':a.data_uuid,'backup_uuid':a.backup_uuid,'apps':','.join(apps),'weekly_backup':getattr(a,'weekly_backup',False),'tz':getattr(a,'tz','America/Ciudad_Juarez'),'base_port':getattr(a,'base_port',18080)}
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
    result={'autoinstall':{'version':1,'interactive-sections':['storage'],'identity':{'hostname':a.name,'username':a.operator,'password':password_hash},'ssh':{'install-server':True,'allow-pw':False,'authorized-keys':[a.ssh_key]},'packages':['docker.io','docker-compose-v2','git','python3','curl','smartmontools','util-linux','python3-socketio','python3-websocket','mdadm','age'],'user-data':{'write_files':files,'runcmd':[['systemctl','daemon-reload'],['systemctl','enable','--now','docker'],['systemctl','enable','srv-jobbi\\x2ddata.mount','mnt-jobbi\\x2dbackup.mount'],['systemctl','enable','jobbi-first-boot.service'],['systemctl','start','--no-block','jobbi-first-boot.service']]}}}
    media_sha=getattr(a,'media_sha',None)
    if media_sha:
        if not re.fullmatch('[a-f0-9]{64}',media_sha):raise ValueError('Invalid offline media identity')
        settings['offline']=True
        files[0]=file('/etc/jobbi/install.json',json.dumps(settings,indent=2),'0600')
        files[1]=file('/usr/local/sbin/jobbi-first-boot',offline_boot(a.commit),'0700')
        ai=result['autoinstall']
        del ai['packages']
        ai['apt']={'fallback':'offline-install','geoip':False}
        ai['refresh-installer']={'update':False}
        ai['updates']='security'
        # The locked digest is part of the customer-private installer seed.
        # Install only named packages through a per-invocation local source.
        from offline_media import PACKAGES
        ai['late-commands']=[
            "cd /cdrom/jobbi-offline && echo '"+media_sha+"  SHA256SUMS' | sha256sum -c - && sha256sum -c SHA256SUMS",
            'test ! -e /target/var/lib/jobbi-offline && cp -r /cdrom/jobbi-offline /target/var/lib/jobbi-offline',
            'chmod 0700 /target/var/lib/jobbi-offline && chmod -R go-rwx /target/var/lib/jobbi-offline/applications',
            'test ! -e /target/var/lib/jobbi-offline-packages && install -d -m 0755 /target/var/lib/jobbi-offline-packages && cp /target/var/lib/jobbi-offline/packages/*.deb /target/var/lib/jobbi-offline/packages/Packages /target/var/lib/jobbi-offline-packages/ && chmod 0644 /target/var/lib/jobbi-offline-packages/*',
            "printf '%s\n' 'deb [trusted=yes] file:/var/lib/jobbi-offline-packages ./' > /target/etc/apt/jobbi-offline.list",
            'curtin in-target -- bash -ec '+shlex.quote(
                'opts=(-o Dir::Etc::sourcelist=/etc/apt/jobbi-offline.list -o Dir::Etc::sourceparts=- -o Dir::State::lists=/var/lib/apt/jobbi-lists); '
                'mkdir -p /var/lib/apt/jobbi-lists/partial; apt-get "${opts[@]}" update; DEBIAN_FRONTEND=noninteractive apt-get "${opts[@]}" --no-install-recommends -y install '+' '.join(PACKAGES)+'; rm -f /etc/apt/jobbi-offline.list; rm -rf /var/lib/apt/jobbi-lists /var/lib/jobbi-offline-packages'),
        ]
    return result

def offline_boot(commit):
    return ('#!/bin/bash\nset -euo pipefail\numask 022\n'
            'root=/opt/jobbi-aio\n'
            'if [[ ! -d "$root/.git" ]]; then test ! -e "$root"; git clone --branch appliance /var/lib/jobbi-offline/release.bundle "$root"; fi\n'
            'test "$(git -C "$root" rev-parse HEAD)" = '+commit+'\n'
            'exec python3 "$root/scripts/first-boot.py" /etc/jobbi/install.json\n')
def remaster_iso(source,config_file,output,media=None):
    if output.exists():raise ValueError('Refuse to overwrite an existing ISO')
    subprocess.run(['xorriso','-indev',str(source),'-outdev',str(output),*(['-iso_level','3','-map',str(media),'/jobbi-offline'] if media else []),'-map',str(config_file),'/autoinstall.yaml','-boot_image','any','replay','-commit','-end'],check=True)
    output.chmod(0o600)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--name');p.add_argument('--profile',type=Path,help='Non-secret installation profile exported by the private dashboard');p.add_argument('--quote',type=Path,help='Customer quote export for app selection');p.add_argument('--operator',default='jobbi');p.add_argument('--commit',required=True);p.add_argument('--data-uuid',required=True);p.add_argument('--backup-uuid',required=True);p.add_argument('--apps');p.add_argument('--tz');p.add_argument('--base-port',type=int);p.add_argument('--weekly-backup',action='store_true',help='Customer approved weekly cold backup downtime');p.add_argument('--ssh-key-file',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--ubuntu-iso',type=Path);p.add_argument('--iso-sha256');p.add_argument('--offline-media',type=Path,help='Verified private provisioning payload from offline_media.py');a=p.parse_args()
    if a.profile and a.quote:p.error('Choose one configuration source')
    profile={}
    if a.profile:
        profile=json.loads(a.profile.read_text())
        if profile.get('schema')!=1 or profile.get('kind')!='jobbi-install-profile':p.error('Invalid installation profile')
    elif a.quote:
        profile=json.loads(a.quote.read_text())
        if profile.get('schema')!=1:p.error('Invalid quote')
    if (a.profile or a.quote) and (not isinstance(profile.get('apps'),list) or any(not isinstance(x,str) for x in profile['apps'])):p.error('Invalid profile app list')
    a.name=a.name or profile.get('name','home')
    a.apps=a.apps or (','.join(profile['apps']) if profile else DEFAULT)
    a.tz=a.tz or profile.get('tz','America/Ciudad_Juarez')
    a.base_port=a.base_port or profile.get('base_port',18080)
    validate(a)
    a.ssh_key=a.ssh_key_file.read_text().strip()
    if '\n' in a.ssh_key or not re.fullmatch(r'(?:ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256) [A-Za-z0-9+/=]+(?: [^\r\n]+)?',a.ssh_key):p.error('Use a single authorized public SSH key')
    if a.ubuntu_iso:
        if not a.iso_sha256 or not re.fullmatch('[a-fA-F0-9]{64}',a.iso_sha256) or not a.ubuntu_iso.is_file():p.error('Provide a regular official ISO and verified SHA256')
        with a.ubuntu_iso.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=a.iso_sha256.lower():p.error('ISO checksum mismatch')
    if a.offline_media:
        if not a.ubuntu_iso:p.error('Offline media requires a remastered Ubuntu ISO')
        from offline_media import verify_media
        a.media_sha=verify_media(a.offline_media,a.commit,a.apps.split(','))
    a.out=a.out.expanduser().resolve()
    if a.out.exists() or a.out==ROOT or ROOT in a.out.parents:p.error('Use a new private directory outside Git')
    if not sys.stdin.isatty():p.error('Use a trusted interactive terminal for the operator password')
    pw=getpass.getpass('New local operator password (12+ characters): ')
    if len(pw)<12 or '\n' in pw or pw!=getpass.getpass('Confirm: '):p.error('Password mismatch or too short')
    hashed=subprocess.check_output(['openssl','passwd','-6','-stdin'],input=pw+'\n',text=True).strip();del pw
    os.umask(0o077);a.out.mkdir(mode=0o700)
    cfg=config(a,hashed);raw=json.dumps(cfg,indent=2)+'\n'
    (a.out/'user-data').write_text('#cloud-config\n'+raw)
    (a.out/'meta-data').write_text('instance-id: jobbi-'+a.name+'\nlocal-hostname: '+a.name+'\n')
    (a.out/'autoinstall.yaml').write_text(raw)
    (a.out/'README.txt').write_text('Customer-specific private seed. Boot the official Ubuntu Server 24.04 installer, select only the approved OS disk interactively, preserve the prepared data and backup filesystems, and inspect the first-boot service. The seed contains the local password hash; do not share or commit. Delete securely when no longer needed.\n')
    if a.ubuntu_iso:
        output=a.out/'jobbi-ubuntu-server.iso'
        remaster_iso(a.ubuntu_iso,a.out/'autoinstall.yaml',output,a.offline_media)
        with output.open('rb') as stream:checksum=hashlib.file_digest(stream,'sha256').hexdigest()
        (a.out/'SHA256SUMS').write_text(checksum+'  '+output.name+'\n')
    print('Private installer seed created at',a.out)
    print('Review disk selection interactively; do not erase data/backup UUIDs. Never distribute this customer-specific seed or password hash.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.CalledProcessError) as e:sys.exit('USB preparation stopped: '+str(e))
