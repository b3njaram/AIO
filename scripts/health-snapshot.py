#!/usr/bin/env python3
"""Publish a minimal read-only, instance-local health snapshot. No secrets, paths or disk serials."""
import argparse,datetime as dt,json,os,re,subprocess,sys,tempfile
from pathlib import Path
from diagnostics import inspect
from backup_mount import mount_identity
ROOT=Path(__file__).resolve().parents[1]
def now():return dt.datetime.now(dt.timezone.utc)
def update_status(release,check=False):
    if not check:return {'state':'not_checked'}
    try:
        r=subprocess.run(['git','ls-remote','--tags','--refs','https://github.com/b3njaram/AIO.git','refs/tags/jobbi-home-v*'],capture_output=True,text=True,timeout=20,check=True)
        tags=[]
        for line in r.stdout.splitlines():
            sha,_,tag=line.partition('\t')
            m=re.fullmatch(r'refs/tags/jobbi-home-v(\d+)\.(\d+)\.(\d+)',tag)
            if m and re.fullmatch('[0-9a-f]{40}',sha):tags.append((tuple(map(int,m.groups())),tag.split('/')[-1],sha))
        if not tags:return {'state':'no_approved_release'}
        version,tag,sha=max(tags)
        # Do not advertise arbitrary branches as releases; an annotated tag may need resolution.
        return {'state':'current' if sha==release.get('aio_commit') else 'review_available','release':tag}
    except (OSError,subprocess.SubprocessError,ValueError):return {'state':'unknown'}
def summarize(instance,dest,expected,devices=(),check_updates=False):
    diag=inspect(instance,devices);release=json.loads((instance/'release.json').read_text())
    backup={'state':'not_verified'}
    try:
        if not dest.is_dir() or mount_identity(dest)!=expected:backup={'state':'mount_unavailable'}
        else:
            m=json.loads((instance/'maintenance.json').read_text())
            stamp=m.get('verified_backup')
            if stamp:
                when=dt.datetime.strptime(stamp.rsplit('-',1)[-1],'%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc)
                backup={'state':'stale' if (now()-when).days>=8 else 'verified','at':when.isoformat()}
            if any('backup' in x.lower() and ('fail' in x.lower() or 'older' in x.lower()) for x in m.get('alerts',[])):backup['state']='review'
    except (OSError,ValueError,KeyError,subprocess.SubprocessError):pass
    smart=diag['smart'] if isinstance(diag['smart'],list) else []
    # Keep raw diagnostics private. Provide only safe health categories, not hardware IDs.
    return {'at':now().isoformat(),'data_free_percent':diag['data_free_percent'],'docker_free_percent':diag['docker_free_percent'],'ram_gib':diag['ram_gib'],'temperature_c':[x['celsius'] for x in diag['thermal_zones'] if isinstance(x.get('celsius'),(int,float))],'drives':[{'state':x['state'],'temperature_c':x.get('temperature_c')} for x in smart],'service_alert_count':len(diag['alerts']),'backup':backup,'updates':update_status(release,check_updates),'onboarding':sorted(json.loads((instance/'onboarding.json').read_text()).keys()) if (instance/'onboarding.json').exists() else []}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('backup',type=Path);p.add_argument('--expected-backup-mount',required=True);p.add_argument('--smart-device',action='append',default=[]);p.add_argument('--check-updates',action='store_true');a=p.parse_args()
    i=a.instance.resolve();out=i/'data/.dashboard-metrics'
    if not out.is_dir() or out.is_symlink():p.error('Metrics directory missing or unsafe')
    payload=summarize(i,a.backup.resolve(),a.expected_backup_mount,a.smart_device,a.check_updates)
    with tempfile.NamedTemporaryFile(dir=out,delete=False) as tmp:
        try:
            tmp.write(json.dumps(payload).encode());tmp.flush();os.fchmod(tmp.fileno(),0o644);os.replace(tmp.name,out/'health.json')
        finally:Path(tmp.name).unlink(missing_ok=True)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Health snapshot unavailable: '+type(e).__name__)
