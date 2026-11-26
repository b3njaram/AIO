#!/usr/bin/env python3
"""Provision a pinned customer appliance once. Never formats storage or repeats a partial install."""
import json,os,pwd,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(*cmd,**kw):subprocess.run(cmd,check=True,**kw)
def main():
    if os.geteuid()!=0:raise ValueError('First boot requires root on the dedicated appliance')
    cfg=json.loads(Path(sys.argv[1]).read_text())
    if not re.fullmatch('[a-f0-9]{40}',cfg['commit']) or subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()!=cfg['commit']:raise ValueError('Pinned checkout mismatch')
    user=pwd.getpwnam(cfg['operator'])
    if user.pw_uid==0:raise ValueError('Non-root operator required')
    roots=[]
    for key,path in [('data_uuid',Path('/srv/jobbi-data')),('backup_uuid',Path('/mnt/jobbi-backup'))]:
        uuid=cfg[key]
        if not re.fullmatch('[A-Za-z0-9-]{8,80}',uuid):raise ValueError('Invalid filesystem UUID')
        run('findmnt','--noheadings','--mountpoint',str(path),'--source','UUID='+uuid,stdout=subprocess.DEVNULL)
        target=path/('jobbi-instances' if key=='data_uuid' else 'jobbi-backups')
        if target.is_symlink():raise ValueError('Refuse symlinked storage')
        if not target.exists():
            target.mkdir(mode=0o700);os.chown(target,user.pw_uid,user.pw_gid)
        if target.stat().st_uid!=user.pw_uid or target.stat().st_mode&0o077:raise ValueError('Review existing customer directory ownership and privacy')
        roots.append(target)
    if roots[0].stat().st_dev==roots[1].stat().st_dev:raise ValueError('Separate mounted filesystems required')
    instance=roots[0]/cfg['name']
    existing=subprocess.check_output(['docker','ps','-aq'],text=True).split()
    env={**os.environ,'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'safe.directory','GIT_CONFIG_VALUE_0':str(ROOT),'HOME':user.pw_dir}
    if existing or instance.exists():
        # Only resume the post-install health setup after a verified completed
        # install at the same pinned release. Never recreate partial data.
        release=json.loads((instance/'release.json').read_text())
        progress=json.loads((instance/'install-progress.json').read_text())
        values=dict(x.split('=',1) for x in (instance/'.env').read_text().splitlines() if '=' in x)
        project='jobbi-'+cfg['name']
        own=subprocess.check_output(['docker','ps','-aq','--filter','label=com.docker.compose.project='+project],text=True).split()
        if (not existing or set(existing)!=set(own) or release.get('aio_commit')!=cfg['commit'] or progress.get('phase')!='services started; onboarding pending' or values.get('INSTANCE_DIR')!=str(instance) or values.get('COMPOSE_PROJECT_NAME')!=project or values.get('OWNER_UID')!=str(user.pw_uid)):
            raise ValueError('Existing or partial installation detected; inspect without overwriting')
        run('runuser','-u',user.pw_name,'--','bash',str(ROOT/'scripts/verify.sh'),str(instance),env=env)
    else:
        if not cfg.get('offline') and 'remote' in cfg['apps'].split(','):run('bash',str(ROOT/'scripts/customer-remote.sh'))
        offline=[]
        if cfg.get('offline'):
            media=Path('/var/lib/jobbi-offline')
            bundle=media/'applications'
            # Private payload is root-owned and readable by this customer operator.
            for item in [media,bundle,*bundle.rglob('*')]:
                if item.is_symlink() or item.stat().st_uid!=0:raise ValueError('Unexpected offline media ownership')
                os.chown(item,0,user.pw_gid)
                item.chmod(0o750 if item.is_dir() else 0o640)
            offline=['--offline-bundle',str(bundle)]
        run('usermod','-aG','docker',user.pw_name)
        run(sys.executable,str(ROOT/'scripts/boot-guard.py'),str(roots[0]),'--apply')
        run('runuser','-u',user.pw_name,'--',sys.executable,str(ROOT/'scripts/setup-customer.py'),'--name',cfg['name'],'--data-root',str(roots[0]),'--backup-root',str(roots[1]),'--apps',cfg['apps'],'--tz',cfg.get('tz','America/Ciudad_Juarez'),'--base-port',str(cfg.get('base_port',18080)),'--defer-health-to-first-boot',*offline,'--apply',env=env)
    # Only stable by-id aliases for whole disks backing the explicitly approved
    # filesystems. Do not auto-select USB devices, other disks or partitions.
    devices=set()
    for key in ('data_uuid','backup_uuid'):
        source=Path('/dev/disk/by-uuid')/cfg[key]
        try:
            rows=json.loads(subprocess.check_output(['lsblk','--json','--inverse','--paths','--output','NAME,TYPE',str(source.resolve(strict=True))],text=True))['blockdevices']
            def walk(xs):
                for x in xs:
                    if x['type']=='disk':devices.add(Path(x['name']).resolve())
                    walk(x.get('children',[]))
            walk(rows)
        except (OSError,ValueError,KeyError,subprocess.CalledProcessError):pass
    aliases=[]
    for disk in devices:
        matches=sorted(x for x in Path('/dev/disk/by-id').glob('*') if re.fullmatch(r'[A-Za-z0-9_.:+-]+',x.name) and x.resolve()==disk)
        if matches:aliases+=['--smart-device',str(matches[0])]
    run(sys.executable,str(ROOT/'scripts/install-health-service.py'),str(roots[0]/cfg['name']),str(roots[1]),'--operator',user.pw_name,*([] if cfg.get('offline') else ['--check-updates']),*aliases,*(['--weekly-backup'] if cfg.get('weekly_backup') else []),'--apply')
    state=Path('/var/lib/jobbi');state.mkdir(mode=0o700,exist_ok=True)
    (state/'first-boot-complete').write_text('Provisioned; onboarding and acceptance pending\n')
    print('First boot completed; operator must finish customer onboarding.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:sys.exit('First boot stopped: '+str(e))
