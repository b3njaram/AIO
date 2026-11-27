#!/usr/bin/env python3
"""Opt-in experimental media sources on a dedicated pilot; never contacts owner services."""
import argparse,fcntl,json,os,re,subprocess,sys
from pathlib import Path
from private_origins import atomic_write
from pilot_media import credentials,soulseek,invidious,token
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--soulseek',action='store_true',help='Customer approves a distinct Soulseek network account and sharing only authorized files');p.add_argument('--invidious-manifest',type=Path,help='Reviewed exact images and upstream source SHA');p.add_argument('--apply',action='store_true');a=p.parse_args()
    i=a.instance.resolve();e=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or e.get('OWNER_UID')!=str(os.getuid()) or e.get('INSTANCE_DIR')!=str(i) or e.get('BIND_IP')!='127.0.0.1' or 'music' not in e.get('COMPOSE_PROFILES','').split(','):raise ValueError('Original isolated music operator required')
    if not a.soulseek and not a.invidious_manifest:p.error('Select an optional provider')
    if i.name!='laptop-test':raise ValueError('Experimental laptop pilot only')
    overlay=i/'deployment/pilot-media.json';state=i/'data/pilot-media';ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(i)]
    if any((i/n).exists() for n in ('.upgrade-hold.json','.backup-running-services','deployment/recovery-images.json')):raise ValueError('Recovery or backup in progress')
    if overlay.exists() or state.exists():raise ValueError('Existing provider setup retained; inspect rather than create another account')
    print('Preview: customer-only media providers; no public ports, no owner account or external fallback. Invidious UI remains loopback-only. Soulseek direct search, not downloader parity.')
    if not a.apply:return
    os.umask(0o077)
    with (i/'.backup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if overlay.exists() or state.exists():raise ValueError('Existing media state')
        state.mkdir(mode=0o700)
        config={'services':{}};services=[]
        if a.soulseek:
            for folder in ('slskd','shares','downloads','incomplete'):(state/folder).mkdir(mode=0o700)
            c=credentials();atomic_write(state/'soulseek.json',json.dumps(c).encode(),0o600)
            config['services'].update(soulseek(i,int(e['OWNER_UID']),int(e['OWNER_GID']),c))
            services+=['slskd','jobbi-music']
        if a.invidious_manifest:
            pins=json.loads(a.invidious_manifest.read_text());rev=pins['source_commit']
            if not re.fullmatch('[a-f0-9]{40}',rev):raise ValueError('Exact Invidious source commit required')
            source=state/'invidious-source'
            subprocess.run(['git','init',str(source)],check=True)
            subprocess.run(['git','-C',str(source),'fetch','--depth=1','https://github.com/iv-org/invidious.git',rev],check=True)
            subprocess.run(['git','-C',str(source),'checkout','--detach','FETCH_HEAD'],check=True)
            if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=rev:raise ValueError('Source identity differs')
            if not (source/'docker/init-invidious-db.sh').is_file() or not (source/'config/sql').is_dir():raise ValueError('Expected database initialization source missing')
            cfg=invidious(i,pins['images'],source,{k:token() for k in ('db','hmac','companion')})
            config['services'].update(cfg['services']);config['volumes']=cfg['volumes'];services+=list(cfg['services'])
        atomic_write(overlay,json.dumps(config).encode(),0o600)
        # Validate without printing secrets. Pull exact declared images before starting.
        subprocess.run(ctl+['config','--quiet'],check=True)
        subprocess.run(ctl+['pull',*[s for s in services if s!='jobbi-music']],check=True)
        subprocess.run(ctl+['up','-d','--no-build',*services],check=True)
        print('Provider containers started; external account login and playback/search still require verification.')
        if a.soulseek:
            print('Soulseek credentials saved privately in the instance. Do not share this file; do not recreate accounts on retry.')
        if a.invidious_manifest:print('Invidious local HTTP UI started on port 18091; public-origin integration is pending.')
        print('Experimental extension is not exact release or backup certified.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:sys.exit('Provider setup stopped: '+type(exc).__name__+'; preserve existing state for review')
