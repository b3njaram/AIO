#!/usr/bin/env python3
"""Prepare and start a new isolated customer instance; never overwrite an existing one."""
import argparse, ipaddress, json, os, re, secrets, shutil, socket, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'navidrome':'83684735def8138100dc1e304d62f0f1ca556357','movies':'d80c1eb6a255a3a6e1f0912a7777bd1461c5a49f'}
DEFAULT='music,movies,photos,files,passwords,tasks,monitor,remote'
PORTS={'DASH_PORT':0,'MUSIC_PORT':1,'NAV_PORT':2,'MOVIE_PORT':3,'PROWLARR_PORT':4,'PHOTO_PORT':5,'CLOUD_PORT':6,'VAULT_PORT':7,'TASK_PORT':8,'DNS_WEB_PORT':9,'MONITOR_PORT':10}
APPS={
'music':('Jobbi Music','Personal music streaming','Tu música personal','MUSIC_PORT','http://jobbi-music:3131/api/status'),
'navidrome':('Navidrome','Music library and first admin setup','Biblioteca y primer administrador','NAV_PORT','http://navidrome:4533/'),
'movies':('StreamHub','Personal movie and TV library','Biblioteca de películas y series','MOVIE_PORT','http://frontend/'),
'photos':('Immich','Photos and videos','Fotos y videos','PHOTO_PORT','http://immich-server:2283/'),
'files':('Nextcloud','Private files','Archivos privados','CLOUD_PORT','http://nextcloud/'),
'passwords':('Vaultwarden','Password manager','Gestor de contraseñas','VAULT_PORT','http://vaultwarden/'),
'tasks':('Vikunja','Tasks and projects','Tareas y proyectos','TASK_PORT','http://vikunja:3456/'),
'dns':('Pi-hole','Network DNS filtering','Filtrado DNS','DNS_WEB_PORT','http://pihole/admin/'),
'monitor':('Uptime Kuma','Service monitoring','Monitoreo de servicios','MONITOR_PORT','http://uptime-kuma:3001/'),
'remote':('Tailscale','Private remote access; configured on the host','Acceso remoto privado; se configura en el equipo',None,None)}
def run(*args):
    subprocess.run(args,check=True)
def reserve(ip,port,kind=socket.SOCK_STREAM):
    with socket.socket(socket.AF_INET,kind) as s: s.bind((ip,port))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name',required=True)
    p.add_argument('--data-root',required=True)
    p.add_argument('--bind',default='127.0.0.1')
    p.add_argument('--base-port',type=int,default=18080)
    p.add_argument('--quote',type=Path,help='Optional exported quote configuration; prices are never trusted')
    p.add_argument('--apps',default=None,help='Comma separated: '+','.join(k for k in APPS if k!='navidrome'))
    p.add_argument('--music-admin',default='owner')
    p.add_argument('--vault-url',default='')
    p.add_argument('--task-url',default='')
    p.add_argument('--tz',default='Etc/UTC')
    p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--allow-private-bootstrap',action='store_true',help='Explicitly permit first-run setup on a trusted private network')
    a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,35}',a.name): p.error('Invalid name')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,48}',a.music_admin): p.error('Invalid admin name')
    if not re.fullmatch(r'[A-Za-z0-9_+/-]+',a.tz): p.error('Invalid timezone')
    ip=ipaddress.IPv4Address(a.bind)
    if not (ip.is_loopback or any(ip in ipaddress.IPv4Network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','100.64.0.0/10'))): p.error('Use explicit loopback, LAN or Tailscale IPv4, never public or wildcard')
    if not ip.is_loopback and not a.allow_private_bootstrap: p.error('First-run accounts must be set up on loopback. Use --allow-private-bootstrap only on an isolated trusted network.')
    if not 1024<=a.base_port<=65525: p.error('Invalid base port')
    selection=a.apps or DEFAULT
    if a.quote:
        q=json.loads(a.quote.read_text())
        if q.get('schema')!=1 or not isinstance(q.get('apps'),list) or any(not isinstance(x,str) for x in q['apps']): p.error('Invalid quote configuration')
        if a.apps is None: selection=','.join(q['apps'])
        print('Quoted storage, mirroring and RAM require separate hardware validation; this script never formats disks.')
    apps=set(filter(None,selection.split(',')))
    if apps-(set(APPS)-{'navidrome'}): p.error('Unknown app IDs')
    if 'dns' in apps and (ip.is_loopback or ip in ipaddress.IPv4Network('100.64.0.0/10')): p.error('Pi-hole requires an explicit LAN address; omit dns for now')
    parent=Path(a.data_root).expanduser().resolve()
    if not parent.is_dir(): p.error('Data root must already exist; verify disk is mounted')
    instance=parent/a.name
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(instance)): p.error('Path must not contain spaces or special characters')
    if instance.exists(): p.error('Instance already exists; refusing to overwrite')
    for u in (a.vault_url,a.task_url):
        if u and not re.fullmatch(r'https?://[A-Za-z0-9.-]+(?::[0-9]+)?/?',u): p.error('Use a simple origin URL')
    if a.vault_url and not a.vault_url.startswith('https://'): p.error('Vaultwarden requires HTTPS')
    run('docker','info','--format','{{.ServerVersion}}')
    run('docker','compose','version')
    project='jobbi-'+a.name
    if subprocess.check_output(['docker','ps','-a','--filter','label=com.docker.compose.project='+project,'--format','{{.ID}}'],text=True).strip(): p.error('Project already exists')
    if subprocess.check_output(['docker','volume','ls','-q','--filter','label=com.docker.compose.project='+project],text=True).strip(): p.error('Project volumes already exist')
    ports={k:a.base_port+v for k,v in PORTS.items()}
    active={'DASH_PORT'}|{APPS[x][3] for x in apps if APPS[x][3]}
    if 'music' in apps: active.add('NAV_PORT')
    if 'movies' in apps: active.add('PROWLARR_PORT')
    for k in active: reserve('127.0.0.1' if k=='PROWLARR_PORT' else a.bind,ports[k])
    if 'dns' in apps:
        reserve(a.bind,53)
        reserve(a.bind,53,socket.SOCK_DGRAM)
    os.umask(0o077)
    instance.mkdir()
    shutil.copytree(ROOT/'deploy',instance/'deployment')
    release={'aio_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'source_pins':{k:v for k,v in PINS.items() if ('music' if k=='navidrome' else 'movies') in apps}}
    (instance/'release.json').write_text(json.dumps(release,indent=2)+'\n')
    data=instance/'data'
    data.mkdir()
    data.chmod(0o755)
    (instance/'sources').mkdir()
    for d in ('navidrome','music','movies','movies/media','prowlarr','torrserver','photos','vaultwarden','pihole','uptime','.dashboard-metrics'):
        folder=data/d
        folder.mkdir(parents=True,exist_ok=True)
        folder.chmod(0o755)
    for repo,profile in [('navidrome','music'),('movies','movies')]:
        if profile in apps:
            target=instance/'sources'/repo
            run('git','init',str(target))
            run('git','-C',str(target),'remote','add','origin','https://github.com/b3njaram/'+repo+'.git')
            run('git','-C',str(target),'fetch','--depth=1','origin',PINS[repo])
            run('git','-C',str(target),'checkout','--detach','FETCH_HEAD')
    config=[]
    for app,(name,en,es,port,probe) in APPS.items():
        if app not in apps and not (app=='navidrome' and 'music' in apps): continue
        e={'id':app,'name':name,'en':en,'es':es,'port':ports.get(port),'probe':probe}
        if app=='dns': e['path']='/admin/'
        if app=='passwords':
            e.update(note='Configure HTTPS and invite owner before use.',noteEs='Configura HTTPS e invita al propietario antes de usar.')
            if a.vault_url: e['url']=a.vault_url
        if app=='tasks' and a.task_url: e['url']=a.task_url
        config.append(e)
    cfg=instance/'dashboard.json'
    cfg.write_text(json.dumps({'name':'Jobbi Home · '+a.name,'apps':config},indent=2)+'\n')
    cfg.chmod(0o644)
    env={'COMPOSE_PROJECT_NAME':project,'COMPOSE_PROFILES':','.join(sorted(apps-{'remote'})),
         'INSTANCE_DIR':str(instance),'BIND_IP':a.bind,'TZ':a.tz,'OWNER_UID':str(os.getuid()),'OWNER_GID':str(os.getgid()),
         'MUSIC_ADMIN':a.music_admin,'MUSIC_HTTPS':'false','VAULT_DOMAIN':a.vault_url or 'http://'+a.bind+':'+str(ports['VAULT_PORT']),
         'TASK_URL':a.task_url or 'http://'+a.bind+':'+str(ports['TASK_PORT'])+'/','PROWLARR_API_KEY':'','TMDB_API_KEY':''}
    for k in ('MUSIC_DB_PASSWORD','MOVIE_SECRET','IMMICH_DB_PASSWORD','CLOUD_DB_PASSWORD','VAULT_ADMIN_TOKEN','TASK_SECRET','TASK_DB_PASSWORD','DNS_PASSWORD'):
        env[k]=secrets.token_hex(32)
    env.update({k:str(v) for k,v in ports.items()})
    (instance/'.env').write_text(''.join(k+'='+v+'\n' for k,v in env.items()))
    cmd=['bash',str(ROOT/'scripts/ctl.sh'),str(instance)]
    run(*cmd,'config','--quiet')
    print('Prepared:',instance,flush=True)
    if not a.prepare_only:
        run(*cmd,'up','-d','--build')
        run(*cmd,'ps')
    print('Dashboard: http://'+a.bind+':'+str(ports['DASH_PORT']))
    print('Complete docs/HANDOFF.md before exposing services or delivering to a customer.')
if __name__=='__main__':
    try: main()
    except (OSError,ValueError,subprocess.CalledProcessError) as e: sys.exit('Stopped: '+str(e)+'; inspect any newly prepared instance before retrying.')
