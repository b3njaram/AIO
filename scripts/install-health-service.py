#!/usr/bin/env python3
"""Install opt-in host-local health timer and interrupted-backup recovery on dedicated Ubuntu."""
import argparse,os,pwd,re,subprocess,sys
from pathlib import Path
from backup_mount import mount_identity
ROOT=Path(__file__).resolve().parents[1]
def safe(path):
    p=Path(path).resolve()
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(p)):raise ValueError('Unsafe systemd path')
    return str(p)
def units(i,b,user,devices,update,weekly=False):
    i,root,python=map(safe,(i,ROOT,sys.executable));b=safe(b) if b is not None else None
    project=Path(i).name
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,35}',project):raise ValueError('Invalid instance name')
    env=dict(x.split('=',1) for x in (Path(i)/'.env').read_text().splitlines() if '=' in x)
    if env.get('INSTANCE_DIR')!=i or env.get('COMPOSE_PROJECT_NAME')!='jobbi-'+project:raise ValueError('Instance identity mismatch')
    account=pwd.getpwnam(user)
    if account.pw_uid==0 or str(account.pw_uid)!=env['OWNER_UID']:raise ValueError('Use original non-root operator')
    if b is None and weekly:raise ValueError('Weekly backup requires independent storage')
    if b is not None and Path(i).stat().st_dev==Path(b).stat().st_dev:raise ValueError('Independent backup required')
    if any(not re.fullmatch(r'/dev/(sd[a-z]+|nvme\d+n\d+|hd[a-z]+|disk/by-id/[A-Za-z0-9_.:+-]+)',d) for d in devices):raise ValueError('Use explicit whole block devices')
    name='jobbi-'+project
    # Read-only SMART needs elevated disk access; root runs only a trusted, root-owned checkout.
    if devices and (ROOT.stat().st_uid!=0 or any(p.stat().st_uid!=0 or p.stat().st_mode&0o022 for p in (ROOT/'scripts').glob('*.py'))):raise ValueError('SMART timer requires reviewed root-owned non-writable release checkout')
    identity=mount_identity(Path(b)) if b else None
    backup_args=(' '+b+' --expected-backup-mount '+identity) if b else ' --no-backup'
    health='[Unit]\nDescription=Jobbi health snapshot\nAfter=docker.service\nRequiresMountsFor='+i+'\n[Service]\nType=oneshot\nUMask=0077\n'+('' if devices else 'User='+user+'\n')+'ExecStart='+python+' '+root+'/scripts/health-snapshot.py '+i +backup_args+''.join(' --smart-device '+d for d in devices)+(' --check-updates' if update else '')+'\n'
    timer='[Unit]\nDescription=Refresh Jobbi health\n[Timer]\nOnBootSec=2min\nOnUnitActiveSec=15min\nUnit='+name+'-health.service\n[Install]\nWantedBy=timers.target\n'
    recovery='[Unit]\nDescription=Resume interrupted Jobbi backup\nAfter=docker.service\nRequires=docker.service\nRequiresMountsFor='+i+'\nConditionPathExists='+i+'/.backup-running-services\n[Service]\nType=oneshot\nUser='+user+'\nUMask=0077\nExecStart=/bin/bash '+root+'/scripts/backup.sh '+i+' --resume\n[Install]\nWantedBy=multi-user.target\n'
    boot='[Unit]\nDescription=Recover existing Jobbi launcher at boot\nAfter=docker.service '+name+'-backup-resume.service\nRequires=docker.service\nWants='+name+'-backup-resume.service\nRequiresMountsFor='+i+'\n[Service]\nType=oneshot\nUser='+user+'\nUMask=0077\nTimeoutStartSec=420\nExecStart='+python+' '+root+'/scripts/boot-recover.py '+i+' --expected-mount '+mount_identity(Path(i))+'\n[Install]\nWantedBy=multi-user.target\n'
    result={name+'-health.service':health,name+'-health.timer':timer,name+'-backup-resume.service':recovery,name+'-boot-recover.service':boot}
    if 'monitor' in env.get('COMPOSE_PROFILES','').split(','):
        result[name+'-monitor-summary.service']='[Unit]\nDescription=Sanitized Jobbi monitoring summary\nAfter=docker.service\nRequiresMountsFor='+i+'\n[Service]\nType=oneshot\nUser='+user+'\nUMask=0077\nNoNewPrivileges=true\nTimeoutStartSec=30\nExecStart='+python+' '+root+'/scripts/monitor-summary.py '+i+'\n'
        result[name+'-monitor-summary.timer']='[Unit]\nDescription=Refresh Jobbi monitoring summary\n[Timer]\nOnBootSec=90s\nOnUnitActiveSec=60s\nUnit='+name+'-monitor-summary.service\n[Install]\nWantedBy=timers.target\n'
    if weekly:
        result[name+'-backup.service']='[Unit]\nDescription=Approved weekly cold backup\nAfter=docker.service\nRequires=docker.service\nRequiresMountsFor='+i+'\n[Service]\nType=oneshot\nUser='+user+'\nUMask=0077\nTimeoutStartSec=infinity\nExecStart='+python+' '+root+'/scripts/maintenance.py '+i+' '+b+' --expected-backup-mount '+identity+' --run-backup\n'
        result[name+'-backup.timer']='[Unit]\nDescription=Weekly customer-approved backup\n[Timer]\nOnCalendar=Sun *-*-* 03:00:00\nPersistent=false\nUnit='+name+'-backup.service\n[Install]\nWantedBy=timers.target\n'
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('backup',type=Path,nargs='?');p.add_argument('--no-backup',action='store_true');p.add_argument('--operator',required=True);p.add_argument('--smart-device',action='append',default=[]);p.add_argument('--check-updates',action='store_true');p.add_argument('--weekly-backup',action='store_true',help='Explicitly approved Sunday 03:00 cold backup downtime');p.add_argument('--apply',action='store_true');a=p.parse_args()
    if a.no_backup != (a.backup is None):p.error('Provide independent backup or explicitly --no-backup')
    result=units(a.instance,a.backup,a.operator,a.smart_device,a.check_updates,a.weekly_backup)
    for name,body in result.items():print(name+'\n'+body)
    if not a.apply:return
    if os.geteuid()!=0:p.error('Run with sudo only on the customer host')
    directory=Path('/etc/systemd/system')
    for name,body in result.items():
        target=directory/name
        if target.is_symlink() or target.exists() and target.read_text()!=body:p.error('Existing unit differs: '+name)
    for name,body in result.items():
        target=directory/name
        if not target.exists():
            with target.open('x') as out:out.write(body)
            target.chmod(0o644)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now',*[x for x in result if x.endswith('.timer')]],check=True)
    subprocess.run(['systemctl','enable',*[x for x in result if x.endswith(('-resume.service','-boot-recover.service'))]],check=True)
    subprocess.run(['systemctl','start',next(x for x in result if x.endswith('-health.service'))],check=True)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Health setup stopped: '+str(e))
