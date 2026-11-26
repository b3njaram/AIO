#!/usr/bin/env python3
"""Opt-in customer-local systemd user timer; defaults to preview."""
import argparse,os,re,shlex,subprocess,sys
from pathlib import Path
from backup_mount import mount_identity
ROOT=Path(__file__).resolve().parents[1]
def safe(p):
    p=p.expanduser().resolve()
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(p)):raise ValueError('Paths must be absolute and contain no spaces')
    return p
def units(instance,dest,hour,minimum,failure_unit=None):
    instance=safe(instance);dest=safe(dest);root=safe(ROOT)
    if not instance.is_dir() or not dest.is_dir() or instance==dest or instance in dest.parents or dest in instance.parents:raise ValueError('Separate existing instance and backup directories required')
    if instance.stat().st_dev==dest.stat().st_dev:raise ValueError('Backup must be on a separate mounted filesystem')
    if not 0<=hour<=23 or minimum<1:raise ValueError('Invalid schedule')
    env=dict(x.split('=',1) for x in (instance/'.env').read_text().splitlines() if '=' in x)
    project=env.get('COMPOSE_PROJECT_NAME','')
    if env.get('INSTANCE_DIR')!=str(instance) or not re.fullmatch(r'jobbi-[a-z0-9-]+',project):raise ValueError('Invalid customer instance')
    name=project+'-backup'
    python=safe(Path(sys.executable))
    service='[Unit]\nDescription=Cold backup for '+project+'\n[Service]\nType=oneshot\nUMask=0077\nExecStart='+str(python)+' '+str(root/'scripts/maintenance.py')+' '+str(instance)+' '+str(dest)+' --minimum-free-gib '+str(minimum)+' --expected-backup-mount '+mount_identity(dest)+' --run-backup\nTimeoutStartSec=infinity\n'
    if failure_unit:
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}\.service',failure_unit) or failure_unit==name+'.service':
            raise ValueError('Choose a separate existing user notification service')
        service=service.replace('[Service]', 'OnFailure='+failure_unit+'\n[Service]')
    timer='[Unit]\nDescription=Weekly backup for '+project+'\n[Timer]\nOnCalendar=Sun *-*-* '+f'{hour:02d}'+':00:00\nPersistent=false\nUnit='+name+'.service\n[Install]\nWantedBy=timers.target\n'
    return name,service,timer
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('destination',type=Path);p.add_argument('--hour',type=int,default=3);p.add_argument('--minimum-free-gib',type=int,default=50);p.add_argument('--enable',action='store_true',help='Customer explicitly approved weekly cold backup downtime');p.add_argument('--failure-unit',help='Existing customer-owned systemd user notification service');a=p.parse_args()
    name,service,timer=units(a.instance,a.destination,a.hour,a.minimum_free_gib,a.failure_unit)
    print(service);print(timer)
    if not a.enable:print('Preview only. Add --enable after customer approval.');return
    if a.failure_unit:
        state=subprocess.check_output(['systemctl','--user','show','--property=LoadState','--value',a.failure_unit],text=True).strip()
        if state!='loaded':raise ValueError('Notification unit is unavailable')
    os.umask(0o077);d=Path.home()/'.config/systemd/user';d.mkdir(parents=True,exist_ok=True)
    for suffix,body in [('service',service),('timer',timer)]:
        target=d/(name+'.'+suffix)
        if target.exists() and target.read_text()!=body:raise ValueError('Existing unit differs; review manually: '+str(target))
    for suffix,body in [('service',service),('timer',timer)]:
        target=d/(name+'.'+suffix)
        if not target.exists():
            with target.open('x') as file:file.write(body)
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    subprocess.run(['systemctl','--user','enable','--now',name+'.timer'],check=True)
    print('Enabled timer. Verify mount persistence, user manager availability and next run.')
    print('Inspect: systemctl --user list-timers '+name+'.timer')
    print('Disable: systemctl --user disable --now '+name+'.timer')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:sys.exit('Schedule stopped: '+str(e))
