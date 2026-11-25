#!/usr/bin/env python3
"""Local first-run guide and progress tracker; no passwords are recorded."""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STEPS={
'navidrome':('Create the first Navidrome owner using MUSIC_ADMIN; upload owned audio and scan.','NAV_PORT'),
'music':('Sign in with the Navidrome owner; test playback, seek and playlist.','MUSIC_PORT'),
'movies':('Create StreamHub owner with create-movie-user.sh; scan owned video in Community > Local media and test playback.','MOVIE_PORT'),
'photos':('Create initial Immich owner privately, upload and retrieve a sample photo.','PHOTO_PORT'),
'files':('Finish Nextcloud admin setup and verify upload/sync.','CLOUD_PORT'),
'passwords':('Configure private HTTPS, invite owner, disable public signups and test recovery.','VAULT_PORT'),
'tasks':('Create owner with task-owner.py; verify registration is disabled and test a task.','TASK_PORT'),
'dns':('Test Pi-hole on one LAN device; document DNS rollback.','DNS_WEB_PORT'),
'monitor':('Create Uptime Kuma owner and set private monitors.','MONITOR_PORT'),
'remote':('Customer enrolls their own Tailscale account; verify ACLs, HTTPS and independent device access.',None)}
def atomic(path,data):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,indent=2)+'\n')
    temp.chmod(0o600)
    temp.replace(path)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('instance',type=Path)
    p.add_argument('--mark',choices=STEPS)
    p.add_argument('--reset',choices=STEPS)
    p.add_argument('--create-movie-owner',metavar='USERNAME')
    p.add_argument('--link-movie-key',action='store_true')
    a=p.parse_args()
    instance=a.instance.resolve()
    env=dict(x.split('=',1) for x in (instance/'.env').read_text().splitlines() if '=' in x and not x.startswith('#'))
    if env.get('INSTANCE_DIR')!=str(instance) or not re.fullmatch(r'jobbi-[a-z0-9-]+',env.get('COMPOSE_PROJECT_NAME','')):p.error('Invalid instance')
    apps=json.loads((instance/'dashboard.json').read_text())['apps']
    selected={x['id'] for x in apps}
    state_file=instance/'onboarding.json'
    state=json.loads(state_file.read_text()) if state_file.exists() else {}
    if any(x not in selected for x in (a.mark,a.reset) if x):p.error('Application not installed')
    if a.create_movie_owner or a.link_movie_key:
        if 'movies' not in selected:p.error('Movies not selected')
        if a.create_movie_owner:subprocess.run(['bash',str(ROOT/'scripts/create-movie-user.sh'),str(instance),a.create_movie_owner],check=True)
        if a.link_movie_key:subprocess.run([sys.executable,str(ROOT/'scripts/connect-movies.py'),str(instance)],check=True)
    if a.mark:
        state[a.mark]='operator confirmed'
        atomic(state_file,state)
    if a.reset:
        state.pop(a.reset,None)
        atomic(state_file,state)
    print('First-run checklist: '+env['COMPOSE_PROJECT_NAME'])
    for app,(task,port) in STEPS.items():
        if app not in selected:continue
        print(('[x]' if app in state else '[ ]')+' '+app+': '+task)
        if port: print('    http://'+env['BIND_IP']+':'+env[port])
    print('Progress: '+str(len(set(state)&selected))+'/'+str(len(selected))+' operator confirmations. Not automated acceptance or security certification.')
    print('See docs/HANDOFF.md and business/ACCEPTANCE.md before customer delivery.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:sys.exit('Onboarding stopped: '+str(e))
