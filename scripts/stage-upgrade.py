#!/usr/bin/env python3
"""Prepare a stopped side-by-side upgrade from a fresh independent cold backup."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from install import PINS
from customer_patches import VERSION, secure_movie_cookies
from restore import verified_archives

ROOT=Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])


def check_release(instance,old,new):
    if not all(re.fullmatch('[a-f0-9]{40}',sha) for sha in (old,new)) or old==new:
        raise ValueError('Specify two distinct full Git commit IDs')
    if git('rev-parse','HEAD').decode().strip()!=new or git('status','--porcelain').strip():
        raise ValueError('Use a clean checkout of the requested target revision')
    subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',old,new],check=True)
    release=json.loads((instance/'release.json').read_text())
    if release['aio_commit']!=old:
        raise ValueError('Installed release differs from expected source')
    if release['customer_patch_version'] not in (2,VERSION) or any(PINS.get(k)!=v for k,v in release['source_pins'].items()):
        raise ValueError('This transition requires a reviewed source migration')
    frozen=instance/'deployment'
    names=git('ls-tree','-r','--name-only',old,'deploy').decode().splitlines()
    expected={name.removeprefix('deploy/') for name in names}
    actual={str(p.relative_to(frozen)) for p in frozen.rglob('*') if not p.is_dir()}
    if actual-{'recovery-images.json'}!=expected:
        raise ValueError('Review locally customized deployment before upgrading')
    for name in names:
        p=frozen/name.removeprefix('deploy/')
        if p.is_symlink() or p.read_bytes()!=git('show',old+':'+name):
            raise ValueError('Frozen service configuration differs from recorded release')
    return release


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('instance',type=Path)
    p.add_argument('backup_root',type=Path)
    p.add_argument('--from-commit',required=True)
    p.add_argument('--to-commit',required=True)
    p.add_argument('--name',required=True)
    p.add_argument('--base-port',type=int,required=True)
    p.add_argument('--minimum-free-gib',type=int,default=50)
    p.add_argument('--prepare',action='store_true',help='Approve cold backup downtime and creation of a separate stopped upgrade')
    a=p.parse_args()
    i=a.instance.resolve()
    backup=a.backup_root.resolve()
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,35}',a.name) or not 1024<=a.base_port<=65524:
        p.error('Invalid candidate name or port range')
    target=i.parent/a.name
    if target.exists() or target.is_symlink():p.error('A new candidate instance is required')
    if not backup.is_dir() or backup.stat().st_dev==i.stat().st_dev or backup in i.parents or i in backup.parents:
        p.error('Mount a separate backup filesystem')
    if a.minimum_free_gib<1 or shutil.disk_usage(backup).free<a.minimum_free_gib*1024**3:
        p.error('Insufficient independent backup capacity')
    release=check_release(i,a.from_commit,a.to_commit)
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if env['INSTANCE_DIR']!=str(i) or env['BIND_IP']!='127.0.0.1':
        p.error('Only dedicated loopback instances support staged upgrades')
    if not a.prepare:
        print('Preflight passed. --prepare cold-backs up the source, verifies exact recovery, and prepares a stopped candidate at',target)
        return
    os.umask(0o077)
    # Use the path reported by this invocation. Concurrent operator backups can
    # never cause selection of a different customer's archive.
    result=subprocess.run(['bash',str(ROOT/'scripts/backup.sh'),str(i),str(backup)],check=True,stdout=subprocess.PIPE,text=True)
    completed=[s.removeprefix('Backup: ').split(' (',1)[0] for s in result.stdout.splitlines() if s.startswith('Backup: ')]
    if len(completed)!=1:raise ValueError('Backup did not report one completed archive')
    snapshot=Path(completed[0])
    if snapshot.parent!=backup or not snapshot.name.startswith(env['COMPOSE_PROJECT_NAME']+'-'):
        raise ValueError('Unexpected backup identity')
    verified_archives(snapshot)
    subprocess.run([sys.executable,str(ROOT/'scripts/restore.py'),str(snapshot),'--require-exact-images','--name',a.name,'--data-root',str(i.parent),'--base-port',str(a.base_port)],check=True)
    if release['customer_patch_version']==2 and 'movies' in release['source_pins']:
        secure_movie_cookies(target)
    release['customer_patch_version']=VERSION
    # Prior deployment, pre-upgrade data, and original running services are retained.
    if (target/'deployment.previous').exists():raise ValueError('Unexpected staged configuration')
    candidate=target/'deployment.next'
    shutil.copytree(ROOT/'deploy',candidate)
    (target/'deployment').rename(target/'deployment.previous')
    candidate.rename(target/'deployment')
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(target)]
    subprocess.run([*ctl,'config','--quiet'],check=True)
    subprocess.run([*ctl,'create','--build','--force-recreate'],check=True)
    release['aio_commit']=a.to_commit
    (target/'release.json').write_text(json.dumps(release,indent=2)+'\n')
    (target/'upgrade.json').write_text(json.dumps({'source':str(i),'backup':str(snapshot),'from':a.from_commit,'to':a.to_commit,'state':'stopped-awaiting-validation'},indent=2)+'\n')
    print('Prepared stopped candidate:',target)
    print('Review outbound integrations and origin settings before isolated testing. Source remains authoritative.')
    print('To abandon a trial after starting it, stop the candidate with ctl.sh. Retain both data sets. Reconcile any post-cutover writes manually.')


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:sys.exit('Upgrade stopped: '+str(e))
