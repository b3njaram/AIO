#!/usr/bin/env python3
"""Preview or execute a guided customer installation on dedicated Ubuntu 24.04 x86-64."""
import argparse,json,os,platform,re,shlex,shutil,subprocess,sys,time
from pathlib import Path
from install import APPS,DEFAULT
ROOT=Path(__file__).resolve().parents[1]
def args():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name',required=True)
    p.add_argument('--data-root',required=True,type=Path)
    p.add_argument('--backup-root',required=True,type=Path)
    p.add_argument('--base-port',type=int,default=18080)
    p.add_argument('--apps')
    p.add_argument('--quote',type=Path)
    p.add_argument('--offline-bundle',type=Path)
    p.add_argument('--tz',default='America/Ciudad_Juarez')
    p.add_argument('--minimum-free-gib',type=int,default=50)
    p.add_argument('--minimum-docker-free-gib',type=int,default=20)
    p.add_argument('--defer-health-to-first-boot',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--weekly-backup',action='store_true',help='Customer approved weekly cold-backup interruption')
    p.add_argument('--apply',action='store_true',help='Confirm dedicated host and reviewed storage, then provision the customer stack')
    return p.parse_args()
def plan(a):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,35}',a.name):raise ValueError('Invalid customer name')
    if not 1024<=a.base_port<=65525 or min(a.minimum_free_gib,a.minimum_docker_free_gib)<1:raise ValueError('Invalid ports or free-space thresholds')
    if not re.fullmatch(r'[A-Za-z0-9_+/-]+',a.tz):raise ValueError('Invalid time zone')
    selected=a.apps
    if a.quote and selected is None:
        q=json.loads(a.quote.read_text())
        if q.get('schema')!=1 or not isinstance(q.get('apps'),list) or any(not isinstance(x,str) for x in q['apps']):raise ValueError('Invalid quote export')
        selected=','.join(q['apps'])
    apps=list(dict.fromkeys((selected if selected is not None else DEFAULT).split(',')))
    if not apps or any(x not in set(APPS)-{'navidrome','dns'} for x in apps):raise ValueError('Select core apps only; Pi-hole requires separate LAN configuration')
    if not any(x!='remote' for x in apps):raise ValueError('Select at least one local application')
    data=a.data_root.expanduser().resolve();backup=a.backup_root.expanduser().resolve()
    for path in (data,backup):
        if path==Path('/') or not path.is_dir() or not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(path)):raise ValueError('Use existing reviewed storage directories, without spaces')
    if data==backup or data in backup.parents or backup in data.parents or data.stat().st_dev==backup.stat().st_dev:
        raise ValueError('Use separate mounted filesystems for data and backup')
    instance=data/a.name
    if instance.exists() or instance.is_symlink():raise ValueError('Instance exists; do not overwrite it. Inspect progress and use ctl.sh after reviewing.')
    common=['--apps',','.join(apps)]
    pre=[sys.executable,str(ROOT/'scripts/preflight.py'),'--data-root',str(data),'--backup-root',str(backup),*common,'--minimum-free-gib',str(a.minimum_free_gib),'--minimum-docker-free-gib',str(a.minimum_docker_free_gib)]
    install=[sys.executable,str(ROOT/'scripts/install.py'),'--name',a.name,'--data-root',str(data),'--base-port',str(a.base_port),'--tz',a.tz,*common]
    if getattr(a,'offline_bundle',None):install+=['--offline-bundle',str(a.offline_bundle.absolute())]
    verify=['bash',str(ROOT/'scripts/verify.sh'),str(instance)]
    onboard=[sys.executable,str(ROOT/'scripts/onboard.py'),str(instance)]
    return instance,pre,install,verify,onboard
def run(command):subprocess.run(command,check=True)
def main():
    a=args()
    instance,pre,install,verify,onboard=plan(a)
    print('Dedicated Ubuntu 24.04 x86-64 customer host; loopback only. No formatting, public access or existing instance changes.')
    for c in (pre,install,verify,onboard):print(shlex.join(c))
    if not a.apply:
        print('Preview only. After checking disks and approving the dedicated host, add --apply.')
        return
    if os.geteuid()==0:raise ValueError('Run as the dedicated non-root operator, not sudo')
    release=platform.freedesktop_os_release()
    if platform.machine()!='x86_64' or release.get('ID')!='ubuntu' or release.get('VERSION_ID')!='24.04':raise ValueError('Automated host setup requires Ubuntu Server 24.04 x86-64')
    if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip():raise ValueError('Use a clean reviewed release checkout')
    if not shutil.which('docker'):
        if a.offline_bundle:raise ValueError('Install offline host prerequisites first')
        run(['sudo','bash',str(ROOT/'scripts/customer-prerequisites.sh'),'--install'])
    if subprocess.run(['docker','info','--format','{{.ServerVersion}}'],check=False).returncode:
        raise ValueError('Docker access required. On this dedicated host only, grant the operator Docker access with sudo usermod -aG docker "$USER", then log out/in and rerun. Docker access is root-equivalent.')
    run(pre)
    if not a.defer_health_to_first_boot and 'remote' in install[install.index('--apps')+1].split(',') and not shutil.which('tailscale'):
        if a.offline_bundle:print('Private remote enrollment deferred until network access is available.')
        else:run(['sudo','bash',str(ROOT/'scripts/customer-remote.sh')])
    # First boot already installs this guard. Manual guided installs require an
    # explicit dedicated-host guard before provisioning customer containers.
    guard=Path('/etc/systemd/system/docker.service.d/90-jobbi-storage.conf')
    if not guard.is_file():run(['sudo',sys.executable,str(ROOT/'scripts/boot-guard.py'),str(instance.parent),'--apply'])
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('boot_guard',ROOT/'scripts/boot-guard.py');module=module_from_spec(spec);spec.loader.exec_module(module)
    target,uuid=module.mount(instance.parent)
    expected='ExecStartPre=/usr/bin/findmnt --noheadings --mountpoint '+target+' --source UUID='+uuid
    if guard.is_symlink() or guard.stat().st_uid!=0 or guard.stat().st_mode&0o022 or expected not in guard.read_text().splitlines():raise ValueError('Existing boot guard does not match the approved data filesystem')
    run(install)
    for attempt in range(12):
        if subprocess.run(verify,check=False).returncode==0:break
        if attempt<11:time.sleep(15)
    else:raise ValueError('Services not all reachable. Existing customer instance retained; inspect ctl.sh INSTANCE ps -a and logs.')
    run(onboard)
    if not a.defer_health_to_first_boot:
        import pwd
        run(['sudo',sys.executable,str(ROOT/'scripts/install-health-service.py'),str(instance),str(a.backup_root.expanduser().resolve()),'--operator',pwd.getpwuid(os.getuid()).pw_name,*(['--check-updates'] if not a.offline_bundle else []),*(['--weekly-backup'] if a.weekly_backup else []),'--apply'])
    print('Services installed; customer onboarding and functional acceptance remain pending.')
    print('Local dashboard: http://127.0.0.1:'+str(a.base_port))
    print('Next: docs/HANDOFF.md, docs/PRIVATE-ACCESS.md, then independent backup and reboot/restore acceptance.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:sys.exit('Customer setup stopped: '+str(e))
