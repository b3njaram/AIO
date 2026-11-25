#!/usr/bin/env python3
"""Scoped owner operations on existing applications; no build, pull, remove or arbitrary shell."""
import argparse,fcntl,json,os,re,subprocess,sys,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SERVICES={'music':'jobbi-music','movies':'frontend','photos':'immich-server','files':'nextcloud','passwords':'vaultwarden','tasks':'vikunja','monitor':'uptime-kuma','dashboard':'dashboard'}
def identity(i):
    env=i/'.env'
    if env.is_symlink() or env.stat().st_mode&0o077:raise ValueError('Private environment required')
    e=dict(x.split('=',1) for x in env.read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or e.get('OWNER_UID')!=str(os.getuid()) or e.get('INSTANCE_DIR')!=str(i) or not re.fullmatch('jobbi-[a-z0-9-]+',e.get('COMPOSE_PROJECT_NAME','')):raise ValueError('Original non-root instance operator required')
    return e
def command(i,*args):
    return ['bash',str(ROOT/'scripts/ctl.sh'),str(i),*args]
def status(i):
    e=identity(i)
    raw=subprocess.check_output(command(i,'ps','-a','--format','json'),text=True,timeout=30)
    rows={}
    for line in raw.splitlines():
        v=json.loads(line)
        for x in v if isinstance(v,list) else [v]:rows[x['Service']]=x
    profiles=set(e['COMPOSE_PROFILES'].split(','))
    return [{'app':a,'state':rows.get(s,{}).get('State','missing'),'health':rows.get(s,{}).get('Health') or 'not_checked'} for a,s in SERVICES.items() if a=='dashboard' or a in profiles]
def restart(i,app,apply=False):
    identity(i)
    current={x['app']:x for x in status(i)}
    if app not in current or app not in SERVICES or current[app]['state']!='running':raise ValueError('Only an existing running application can be restarted')
    if not apply:return {'app':app,'operation':'restart','applied':False}
    with (i/'.backup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if any((i/x).exists() for x in ('.upgrade-hold.json','.backup-running-services')):raise ValueError('Backup or update in progress')
        # No Compose up/build; only restart the existing single application container.
        subprocess.run(command(i,'restart','--timeout','30',SERVICES[app]),check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120)
    return {'app':app,'operation':'restart','applied':True,'status':status(i)}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('action',choices=['status','restart']);p.add_argument('--app',choices=list(SERVICES));p.add_argument('--apply',action='store_true');a=p.parse_args();i=a.instance.resolve()
    print(json.dumps(status(i) if a.action=='status' else restart(i,a.app,a.apply),indent=2))
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Application operation refused: '+type(e).__name__)
