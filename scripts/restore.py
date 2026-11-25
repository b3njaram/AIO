#!/usr/bin/env python3
"""Restore a trusted AIO cold backup into a NEW, loopback-only instance.
Never points at an existing instance or starts services automatically.
"""
import argparse,hashlib,json,os,re,shutil,subprocess,sys,tarfile
from pathlib import Path,PurePosixPath
from install import PORTS, reserve, APPS
from customer_patches import apply
from recovery_images import stage
ROOT=Path(__file__).resolve().parents[1]
ALLOWED_REPOS={'navidrome','movies'}
def run(*args):subprocess.run(args,check=True)
def output(*args):return subprocess.check_output(args,text=True).strip()
def checksum(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def verified_archives(root):
    result={}
    for line in (root/'SHA256SUMS').read_text().splitlines():
        m=re.fullmatch(r'([0-9a-f]{64}) [ *](?:\./)?([A-Za-z0-9_-]+\.tar\.gz)',line)
        if not m:raise ValueError('Malformed backup checksum list')
        name=m[2];p=root/name
        if name in result or p.is_symlink() or not p.is_file() or checksum(p)!=m[1]:raise ValueError('Missing or invalid archive: '+name)
        result[name]=p
    if 'instance.tar.gz' not in result:raise ValueError('No instance archive')
    return result
def validate_archive(path,instance=False):
    with tarfile.open(path,'r:gz') as tar:
        seen=set()
        for m in tar:
            n=PurePosixPath(m.name)
            if n.is_absolute() or '..' in n.parts or m.name.startswith('/'):raise ValueError('Unsafe archive path')
            name=str(n)
            if name in seen:raise ValueError('Duplicate archive member')
            seen.add(name)
            if instance and n.parts and n.parts[0] not in ('.env','dashboard.json','release.json','deployment','data','onboarding.json','image-inventory.json'):raise ValueError('Unexpected instance member')
            # Reject links escaping their own archive; no device files or FIFOs.
            if m.issym() or m.islnk():
                target=PurePosixPath(m.linkname)
                if instance or target.is_absolute() or '..' in target.parts:raise ValueError('Unsafe or unsupported archive link')
            elif not (m.isfile() or m.isdir()):raise ValueError('Unsupported archive member')
        if instance and not {'.env','dashboard.json','release.json','deployment/compose.yaml'}<=seen:raise ValueError('Backup predates frozen deployment; manual restore required')
def metadata(path):
    with tarfile.open(path,'r:gz') as t:
        def read(n):
            m=t.getmember(n)
            if not m.isfile() or m.size>1024*1024:raise ValueError('Invalid metadata')
            return t.extractfile(m).read().decode()
        env=dict(x.split('=',1) for x in read('.env').splitlines() if '=' in x and not x.startswith('#'))
        cfg=json.loads(read('dashboard.json'))
        release=json.loads(read('release.json'))
        return env,cfg,release
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('backup',type=Path);p.add_argument('--data-root',type=Path,required=True);p.add_argument('--name',required=True);p.add_argument('--base-port',type=int,default=19080);p.add_argument('--require-exact-images',action='store_true',help='Stop before volume restore if recorded image IDs differ')
    a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,35}',a.name) or not 1024<=a.base_port<=65525:p.error('Invalid name or port')
    backup=a.backup.resolve();parent=a.data_root.expanduser().resolve();dest=parent/a.name;project='jobbi-'+a.name
    if not parent.is_dir() or dest.exists() or not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(dest)) or not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(backup)):p.error('Use existing data root, new instance path and paths without spaces')
    if dest==backup or dest in backup.parents or backup in dest.parents:p.error('Backup and restore location must be separate')
    archives=verified_archives(backup)
    local_images=archives.pop("local-images.tar.gz",None)
    for n,path in archives.items():validate_archive(path,n=='instance.tar.gz')
    env,cfg,release=metadata(archives['instance.tar.gz'])
    old=env.get('COMPOSE_PROJECT_NAME','')
    if not re.fullmatch(r'jobbi-[a-z0-9-]+',old) or old==project:p.error('Restore must have a new project name')
    dns='dns' in env.get('COMPOSE_PROFILES','').split(',')
    if dns:
        if 'DNS_LISTEN_PORT' not in env or a.base_port+11>65535:p.error('Legacy DNS installation requires a manual private restore')
        reserve('127.0.0.1',a.base_port+11)
        import socket
        reserve('127.0.0.1',a.base_port+11,socket.SOCK_DGRAM)
        env['DNS_LISTEN_PORT']=str(a.base_port+11)
    if env.get('OWNER_UID')!=str(os.getuid()) or env.get('OWNER_GID')!=str(os.getgid()):p.error('Restore using the original installation UID/GID; manual ownership migration otherwise')
    version=release.get('customer_patch_version',0)
    if version not in (0,1,2):p.error('Unknown customer patch version')
    pins=release.get('source_pins',{})
    if any(k not in ALLOWED_REPOS or not re.fullmatch('[0-9a-f]{40}',v) for k,v in pins.items()):p.error('Unsupported source pins')
    volumes={}
    for n,path in archives.items():
        if n=='instance.tar.gz':continue
        if not n.startswith(old+'_'):p.error('Unexpected volume archive')
        suffix=n[len(old)+1:-7]
        if not re.fullmatch(r'[a-z0-9-]+',suffix):p.error('Invalid volume name')
        volumes[suffix]=path
    for cmd in [('docker','ps','-a'),('docker','volume','ls'),('docker','network','ls')]:
        if output(*cmd,'-q','--filter','label=com.docker.compose.project='+project):p.error('Destination Docker project already exists')
    for port in PORTS.values():reserve('127.0.0.1',a.base_port+port)
    os.umask(0o077);dest.mkdir()
    # Docker preserves original numeric ownership; archive already validated.
    run('docker','run','--rm','--network','none','-v',str(backup)+':/backup:ro','-v',str(dest)+':/dst:rw','alpine:3.22@sha256:49340b346798875b5592e5d420241f2f9cfba5f47e62ebb1446a1b34734e898f','tar','xzf','/backup/instance.tar.gz','-C','/dst')
    # Rewrite only non-secret installation identity and network values.
    oldports={int(env[k]):a.base_port+n for k,n in PORTS.items() if k in env}
    env.update({'INSTANCE_DIR':str(dest),'COMPOSE_PROJECT_NAME':project,'BIND_IP':'127.0.0.1','MUSIC_HTTPS':'false',
                'VAULT_DOMAIN':'http://127.0.0.1:'+str(a.base_port+PORTS['VAULT_PORT']),
                'TASK_REGISTRATION':'false','TASK_URL':'http://127.0.0.1:'+str(a.base_port+PORTS['TASK_PORT'])+'/'})
    env.update({k:str(a.base_port+n) for k,n in PORTS.items()})
    (dest/'.env').write_text(''.join(k+'='+v+'\n' for k,v in env.items()));(dest/'.env').chmod(0o600)
    cfg['name']='Jobbi Home · '+a.name
    for app in cfg['apps']:
        app.pop('url',None)
        if app.get('port') in oldports:app['port']=oldports[app['port']]
    (dest/'dashboard.json').write_text(json.dumps(cfg,indent=2)+'\n');(dest/'dashboard.json').chmod(0o644)
    # Clone only known source repositories from the captured release.
    (dest/'sources').mkdir()
    oldmask=os.umask(0o022)
    try:
        for repo,sha in pins.items():
            folder=dest/'sources'/repo
            run('git','init',str(folder))
            run('git','-C',str(folder),'remote','add','origin','https://github.com/b3njaram/'+repo+'.git')
            run('git','-C',str(folder),'fetch','--depth=1','origin',sha)
            run('git','-C',str(folder),'checkout','--detach','FETCH_HEAD')
            if version:apply(dest,repo,version)
    finally:os.umask(oldmask)
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(dest)]
    inventory=dest/'image-inventory.json'
    exact=inventory.is_file() and (local_images is not None or a.require_exact_images)
    if exact:
        stage(json.loads(inventory.read_text()),local_images,dest/'deployment')
    run(*ctl,'config','--quiet')
    # Compose creates named volumes; no service starts before recovery is complete.
    run(*ctl,'create',*(['--no-build','--pull','never'] if exact else ['--build']))
    available=set(output('docker','volume','ls','-q','--filter','label=com.docker.compose.project='+project).splitlines())
    expected_volumes={project+'_'+suffix for suffix in volumes}
    if available!=expected_volumes:raise ValueError('Backup volume set does not match destination; inspect before recovery')
    inventory=dest/'image-inventory.json'
    if inventory.exists():
        result=subprocess.run([sys.executable,str(ROOT/'scripts/release-inventory.py'),str(dest),'--compare',str(inventory)])
        if result.returncode:
            if exact:raise ValueError('Image identity differs or cannot be verified; no named volume restored')
            print('WARNING: image identity differs or could not be verified. Do not start until reviewed.')
    elif a.require_exact_images:raise ValueError('Backup lacks image inventory; strict recovery cannot continue')
    for suffix,path in volumes.items():
        volume=project+'_'+suffix
        if volume not in available:raise ValueError('Backup volume not defined in new project: '+suffix)
        run('docker','run','--rm','--network','none','-v',str(backup)+':/backup:ro','-v',volume+':/dst:rw','alpine:3.22@sha256:49340b346798875b5592e5d420241f2f9cfba5f47e62ebb1446a1b34734e898f','sh','-c','find /dst -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +; tar xzf "/backup/$1" -C /dst','sh',path.name)
    print('Restored into stopped project: '+project)
    print('Inspect release, image versions, ports, credentials and domains. Then explicitly start with ctl.sh INSTANCE up -d.')
    print('Never expose a recovered copy while the original is serving users. Verify application data and customer ownership.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,tarfile.TarError,subprocess.CalledProcessError) as e:sys.exit('Restore stopped safely: '+str(e)+'; inspect the new destination, never overwrite the original.')
