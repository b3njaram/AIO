#!/usr/bin/env python3
"""Archive exact committed sources and the locally available pinned restore helper."""
import argparse,json,os,re,sys,subprocess
from pathlib import Path
from offline_kit import HELPER,REPOS,archive,cmd,digest,verify
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    i=a.instance.resolve();out=a.output.expanduser().absolute();parent=out.parent.resolve()
    if out.exists() or out.is_symlink() or not parent.is_dir() or parent==ROOT or ROOT in parent.parents or parent==i or i in parent.parents:raise ValueError('New private directory outside repository and instance required')
    release=json.loads((i/'release.json').read_text());sha=release['aio_commit'];pins=release['source_pins']
    if not re.fullmatch('[a-f0-9]{40}',sha) or set(pins)-REPOS or any(not re.fullmatch('[a-f0-9]{40}',x) for x in pins.values()):raise ValueError('Unsupported release')
    for name,pin in pins.items():
        source=i/'sources'/name
        if cmd('git','-C',str(source),'rev-parse','HEAD')!=pin:raise ValueError('Installed source pin differs')
    if cmd('git','-C',str(ROOT),'rev-parse',sha+'^{commit}')!=sha:raise ValueError('Exact AIO commit not available in this checkout')
    identity=cmd('docker','image','inspect','--format','{{.Id}}',HELPER)
    if not re.fullmatch('sha256:[a-f0-9]{64}',identity):raise ValueError('Pinned helper not available locally; complete a backup first')
    print('Recovery kit: exact committed source archives and pinned helper only. No customer data, .env, application credentials or backup contents.')
    if not a.apply:return
    os.umask(0o077);out.mkdir(mode=0o700)
    archive(ROOT,sha,out/'aio-source.tar.gz')
    for name,pin in pins.items():archive(i/'sources'/name,pin,out/(name+'-source.tar.gz'))
    subprocess.run(['docker','image','save','-o',str(out/'helper.tar.gz'),identity],check=True)
    files={x.name:digest(x) for x in out.iterdir()}
    (out/'kit.json').write_text(json.dumps({'schema':1,'release':sha,'source_pins':pins,'helper_id':identity,'helper_reference':HELPER,'files':files},indent=2)+'\n')
    verify(out,release)
    print('Kit verified. Store privately alongside an independent all-images backup; review upstream redistribution obligations.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as e:sys.exit('Kit creation stopped: '+type(e).__name__)
