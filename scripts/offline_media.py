"""Assemble private Ubuntu provisioning media from verified APT packages and an AIO application bundle."""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from install_bundle import check
from offline_kit import digest

ROOT=Path(__file__).resolve().parents[1]
PACKAGES=['docker.io','docker-compose-v2','git','python3','curl','openssh-server','smartmontools','util-linux','python3-socketio','mdadm','age']

def inventory(root):
    result={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError('Media contains a link or special file')
        name=path.relative_to(root).as_posix()
        if not re.fullmatch(r'[A-Za-z0-9%_./+:~-]+',name):raise ValueError('Unexpected media filename')
        if path.is_file() and name!='SHA256SUMS':result[name]=digest(path)
    return ''.join(f'{sha}  {name}\n' for name,sha in result.items())

def verify_media(root,sha,apps):
    if root.is_symlink() or not root.is_dir():raise ValueError('Invalid media directory')
    if (root/'SHA256SUMS').read_text()!=inventory(root):raise ValueError('Media contents differ from manifest')
    meta=json.loads((root/'media.json').read_text())
    if meta!={'schema':1,'commit':sha,'apps':sorted(apps),'os':'ubuntu-24.04-amd64'}:raise ValueError('Media release or app selection mismatch')
    return digest(root/'SHA256SUMS')

def build(bundle,out):
    release=json.loads((bundle/'bundle.json').read_text())
    sha=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    if release['release']['aio_commit']!=sha:raise ValueError('Check out the exact application bundle release')
    if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip():raise ValueError('Clean release checkout required')
    if subprocess.check_output(['git','-C',str(ROOT),'rev-parse','--is-shallow-repository'],text=True).strip()=='true':raise ValueError('Use a full release checkout to create a standalone Git bundle')
    check(bundle,release['release'],release['apps'])
    osinfo=platform.freedesktop_os_release()
    if (osinfo['ID'],osinfo['VERSION_ID'],platform.machine())!=('ubuntu','24.04','x86_64'):
        raise ValueError('Use an Ubuntu 24.04 amd64 preparation workstation with refreshed official Ubuntu APT indexes')
    if out.exists() or out.is_symlink() or not out.parent.is_dir() or any(p==out or p in out.parents for p in (ROOT,bundle)):
        raise ValueError('Use a new directory outside the repository and bundle')
    sources=Path('/etc/apt/sources.list.d/ubuntu.sources')
    if not sources.is_file():raise ValueError('Standard Ubuntu deb822 package sources required')
    os.umask(0o077)
    out.mkdir()
    repo=out/'packages'
    repo.mkdir()
    with tempfile.TemporaryDirectory() as temp:
        bare=Path(temp)/'git'
        subprocess.run(['git','init','--bare',str(bare)],check=True)
        subprocess.run(['git','-C',str(bare),'fetch',str(ROOT),sha+':refs/heads/appliance'],check=True)
        subprocess.run(['git','-C',str(bare),'bundle','create',str(out/'release.bundle'),'refs/heads/appliance'],check=True)
    # An empty status file includes dependencies already present on the workstation.
    # APT verifies the archives against its authenticated package indexes.
    subprocess.run(['apt-get','-y','--download-only','--no-install-recommends',
                    '-o','Dir::Etc::sourcelist='+str(sources),'-o','Dir::Etc::sourceparts=-','-o','Debug::NoLocking=1','-o','Dir::State::status=/dev/null',
                    '-o','Dir::Cache::archives='+str(repo),'install',*PACKAGES],check=True)
    for name in ('partial','auxfiles'):
        if (repo/name).is_dir():shutil.rmtree(repo/name)
    (repo/'lock').unlink(missing_ok=True)
    if not list(repo.glob('*.deb')):raise ValueError('APT returned no packages')
    with (repo/'Packages').open('xb') as f:
        subprocess.run(['dpkg-scanpackages','--multiversion','.','/dev/null'],cwd=repo,stdout=f,check=True)
    shutil.copytree(bundle,out/'applications')
    (out/'media.json').write_text(json.dumps({'schema':1,'commit':sha,'apps':sorted(release['apps']),'os':'ubuntu-24.04-amd64'}))
    (out/'SHA256SUMS').write_text(inventory(out))
    print('Verified private media manifest',verify_media(out,sha,release['apps']))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:build(args.bundle.resolve(),args.out.absolute())
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as err:sys.exit('Media preparation stopped: '+str(err))
