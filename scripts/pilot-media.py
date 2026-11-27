#!/usr/bin/env python3
"""Opt-in experimental media sources on a dedicated pilot; never contacts owner services."""
import argparse,fcntl,json,os,re,subprocess,sys
from pathlib import Path
from private_origins import atomic_write
from pilot_media import SOULSEEK_LOGIN_PROBE,credentials,soulseek,invidious,invidious_credentials,public_origin,local_fallback_source
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--soulseek',action='store_true',help='Customer approves a distinct Soulseek network account and sharing only authorized files');provider=p.add_mutually_exclusive_group();provider.add_argument('--invidious',dest='invidious_manifest',action='store_const',const=ROOT/'deploy/invidious-pilot.json',help='Use the repository-pinned Invidious pilot images');provider.add_argument('--invidious-manifest',type=Path,help='Reviewed exact images and upstream source SHA');p.add_argument('--invidious-public-url',help='Exact customer-owned private HTTPS route, already approved and configured');p.add_argument('--apply',action='store_true');a=p.parse_args()
    i=a.instance.resolve();e=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or e.get('OWNER_UID')!=str(os.getuid()) or e.get('INSTANCE_DIR')!=str(i) or e.get('BIND_IP')!='127.0.0.1' or 'music' not in e.get('COMPOSE_PROFILES','').split(','):raise ValueError('Original isolated music operator required')
    if not a.soulseek and not a.invidious_manifest:p.error('Select an optional provider')
    if a.invidious_public_url and not a.invidious_manifest:p.error('Public origin requires local Invidious')
    public=public_origin(a.invidious_public_url) if a.invidious_public_url else None
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
            # Only upstream public SQL and init script need container read access.
            # Keep the surrounding provider state and generated secrets private.
            public_files=[source/'docker/init-invidious-db.sh',source/'config/sql',*(source/'config/sql').rglob('*')]
            for item in public_files:
                if item.is_symlink() or not (item.is_dir() or item.is_file()):raise ValueError('Unexpected database initialization entry')
                item.chmod(0o755 if item.is_dir() or item.name=='init-invidious-db.sh' else 0o644)
            cfg=invidious(i,pins['images'],source,invidious_credentials())
            config['services'].update(cfg['services']);config['volumes']=cfg['volumes'];services+=list(cfg['services'])
        if public:
            # AIO-only patch to the instance's frozen Jobbi Music checkout, never upstream owner repo.
            target=i/'sources/navidrome/jobbi-music/server/invidious.js'
            if target.is_symlink():raise ValueError('Unexpected music source link')
            original=target.read_text();patched=local_fallback_source(original)
            atomic_write(state/'invidious-adapter.before',original.encode(),0o600)
            atomic_write(target,patched.encode(),0o644)
            cfg=json.loads(config['services']['invidious']['environment']['INVIDIOUS_CONFIG']);from urllib.parse import urlsplit
            u=urlsplit(public);cfg.update(domain=u.hostname,external_port=u.port,https_only=True)
            config['services']['invidious']['environment']['INVIDIOUS_CONFIG']=json.dumps(cfg)
            config['services'].setdefault('jobbi-music',{}).setdefault('environment',{}).update(JOBBI_LOCAL_INVIDIOUS='true',JOBBI_INVIDIOUS_PUBLIC_ORIGIN=public,INVIDIOUS_URL='disabled',INVIDIOUS_BACKUPS='')
            if 'jobbi-music' not in services:services.append('jobbi-music')
        atomic_write(overlay,json.dumps(config).encode(),0o600)
        # Validate without printing secrets. Pull exact declared images before starting.
        subprocess.run(ctl+['config','--quiet'],check=True)
        registry_services=[s for s in services if s not in ('jobbi-music','slskd','invidious','invidious-db')]
        if registry_services:subprocess.run(ctl+['pull',*registry_services],check=True)
        if a.soulseek:subprocess.run(ctl+['build','slskd'],check=True)
        if a.invidious_manifest:subprocess.run(ctl+['build','invidious','invidious-db'],check=True)
        if public:subprocess.run(ctl+['build','jobbi-music'],check=True)
        subprocess.run(ctl+['up','-d','--no-build',*services],check=True)
        print('Provider containers started; external account login and playback/search still require verification.')
        if a.soulseek:
            print('Soulseek credentials saved privately in the instance. Do not share this file; do not recreate accounts on retry.')
            import time
            for attempt in range(12):
                if subprocess.run(ctl+['exec','-T','jobbi-music','node','--input-type=module','-e',SOULSEEK_LOGIN_PROBE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
                    print('Soulseek network authentication verified');break
                time.sleep(5)
            else:print('Soulseek login not yet verified; retain credentials and review provider state')
        if a.invidious_manifest:print('Invidious local UI started on port 18091; '+('own-instance fallback configured; verify actual route and playback' if public else 'fallback remains disabled until private HTTPS route is approved'))
        print('Experimental extension is not exact release or backup certified.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:sys.exit('Provider setup stopped: '+type(exc).__name__+'; preserve existing state for review')
