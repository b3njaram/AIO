#!/usr/bin/env python3
"""Explicitly configured cold backups; no automatic upgrades or deletion."""
import argparse,datetime as dt,fcntl,json,os,re,shutil,subprocess,sys
from pathlib import Path
from restore import verified_archives
from diagnostics import inspect
from backup_mount import mount_identity
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('destination',type=Path);p.add_argument('--minimum-free-gib',type=int,default=50);p.add_argument('--max-backup-age-days',type=int,default=8);p.add_argument('--run-backup',action='store_true',help='Explicit consent to interrupt only this instance');p.add_argument('--smart-device',action='append',default=[]);p.add_argument('--expected-backup-mount',help='Fingerprint captured when scheduling');a=p.parse_args()
    i=a.instance.resolve();d=a.destination.resolve()
    if a.minimum_free_gib<1 or a.max_backup_age_days<1 or not d.is_dir() or i==d or i in d.parents or d in i.parents: p.error('Use separate existing backup directory and positive limits')
    if a.expected_backup_mount and mount_identity(d)!=a.expected_backup_mount:p.error('Backup mount changed or disappeared; verify the intended disk')
    if i.stat().st_dev==d.stat().st_dev:p.error('Backup destination must be on a separate mounted filesystem')
    os.umask(0o077)
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if env.get('INSTANCE_DIR')!=str(i):p.error('Instance path mismatch')
    project=env.get('COMPOSE_PROJECT_NAME','')
    if not re.fullmatch(r'jobbi-[a-z0-9-]+',project):p.error('Invalid project')
    with (i/'.maintenance.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        alerts=[];before=set(d.glob(project+'-*'))
        if a.run_backup:
            if shutil.disk_usage(d).free<a.minimum_free_gib*1024**3:p.error('Backup filesystem low on space')
            # Existing backup script stops/restarts only this project's running services.
            result=subprocess.run(['bash',str(ROOT/'scripts/backup.sh'),str(i),str(d)],check=False)
            if result.returncode:alerts.append('Backup command failed')
            else:
                new=set(d.glob(project+'-*'))-before
                if len(new)!=1:alerts.append('Expected one new backup directory')
                else:
                    try:verified_archives(next(iter(new)))
                    except (OSError,ValueError):alerts.append('New backup checksum verification failed')
        candidates=sorted((x for x in d.glob(project+'-*') if re.fullmatch(re.escape(project)+r'-[0-9]{8}T[0-9]{6}Z',x.name) and x.is_dir() and not x.is_symlink() and (x/'SHA256SUMS').is_file()),key=lambda x:x.name,reverse=True)
        newest=None
        if candidates:
            try:
                verified_archives(candidates[0]);newest=candidates[0].name
                age=dt.datetime.now(dt.timezone.utc)-dt.datetime.strptime(newest[len(project)+1:],'%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc)
                if age.days>=a.max_backup_age_days:alerts.append('Verified backup older than configured limit')
            except (OSError,ValueError):alerts.append('Latest backup failed integrity check')
        else:alerts.append('No completed backup')
        diag=inspect(i,a.smart_device);alerts+=diag['alerts']
        state={'time':dt.datetime.now(dt.timezone.utc).isoformat(),'verified_backup':newest,'alerts':alerts,'diagnostics':diag,'retention':'manual; never deletes backups','updates':'manual approval required'}
        tmp=i/'maintenance.tmp';tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(i/'maintenance.json')
        print(json.dumps(state,indent=2));return bool(alerts)
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError) as e:sys.exit('Maintenance stopped: '+str(e))
