#!/usr/bin/env python3
"""Prepare origin changes as the instance operator, with existing journaled rollback."""
import ipaddress,json,os,subprocess,sys
from pathlib import Path
from private_origins import prepare,rollback
import nextcloud_origin
ROOT=Path(__file__).resolve().parents[1]
def main():
    i=Path(sys.argv[1]).resolve();addr=str(ipaddress.IPv4Address(sys.argv[2]))
    if not any(ipaddress.IPv4Address(addr) in ipaddress.IPv4Network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):raise ValueError('Lab LAN only')
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or env.get('OWNER_UID')!=str(os.getuid()) or env.get('INSTANCE_DIR')!=str(i) or env.get('BIND_IP')!='127.0.0.1':raise ValueError('Original isolated operator required')
    cfg=json.loads((i/'dashboard.json').read_text());apps={a['id'] for a in cfg['apps']}
    if apps-set('music navidrome movies photos files passwords tasks monitor'.split()):raise ValueError('Unexpected pilot apps')
    keys={'music':'MUSIC_PORT','navidrome':'NAV_PORT','movies':'MOVIE_PORT','photos':'PHOTO_PORT','files':'CLOUD_PORT','passwords':'VAULT_PORT','tasks':'TASK_PORT','monitor':'MONITOR_PORT'}
    urls={k:'https://'+addr+':'+str(int(env[keys[k]])) for k in apps}
    services=['dashboard']+[v for k,v in [('music','jobbi-music'),('movies','backend'),('movies','frontend'),('passwords','vaultwarden'),('tasks','vikunja')] if k in apps]
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(i),'up','-d','--force-recreate','--no-deps','--no-build','--pull','never',*services]
    def undo():
        nextcloud_origin.rollback(i)
        if (i/'.private-origins').exists():rollback(i)
        subprocess.run(ctl,check=True)
    if len(sys.argv)>3 and sys.argv[3]=='--rollback':undo();return
    if any((i/n).exists() for n in ('.private-serve.json','.private-origins','.nextcloud-origin.json','.upgrade-hold.json','.backup-running-services')):raise ValueError('Existing origin transaction or maintenance; review')
    updates={}
    if 'music' in apps:updates['MUSIC_HTTPS']='true'
    if 'movies' in apps:updates['MOVIE_HTTPS']='true'
    if 'passwords' in apps:updates['VAULT_DOMAIN']=urls['passwords']
    if 'tasks' in apps:updates['TASK_URL']=urls['tasks']+'/'
    proposed={**cfg,'apps':[{**a,'url':urls[a['id']]} for a in cfg['apps']]}
    try:
        prepare(i,proposed,updates)
        if 'files' in apps:nextcloud_origin.prepare(i,urls['files'],allow_lab=True)
        subprocess.run(ctl,check=True)
    except BaseException:
        undo();raise
if __name__=='__main__':main()
