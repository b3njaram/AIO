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
    if subprocess.check_output(['docker','ps','-aq'],text=True).strip():raise ValueError('Existing containers detected; inspect interrupted provisioning manually')
    run('usermod','-aG','docker',user.pw_name)
    run(sys.executable,str(ROOT/'scripts/boot-guard.py'),str(roots[0]),'--apply')
    env={**os.environ,'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'safe.directory','GIT_CONFIG_VALUE_0':str(ROOT),'HOME':user.pw_dir}
    run('runuser','-u',user.pw_name,'--',sys.executable,str(ROOT/'scripts/setup-customer.py'),'--name',cfg['name'],'--data-root',str(roots[0]),'--backup-root',str(roots[1]),'--apps',cfg['apps'],'--apply',env=env)
    state=Path('/var/lib/jobbi');state.mkdir(mode=0o700,exist_ok=True)
    (state/'first-boot-complete').write_text('Provisioned; onboarding and acceptance pending\n')
    print('First boot completed; operator must finish customer onboarding.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:sys.exit('First boot stopped: '+str(e))
