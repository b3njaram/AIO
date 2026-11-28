#!/usr/bin/env python3
"""Build private offline application install media from an exact reference instance."""
import argparse,importlib.util,json,os,subprocess,sys
from pathlib import Path
from offline_kit import digest
from install_bundle import check
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('inventory',ROOT/'scripts/release-inventory.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
    i=a.instance.resolve();b=a.output.expanduser().absolute();parent=b.parent.resolve()
    if b.exists() or b.is_symlink() or not parent.is_dir() or any(x==parent or x in parent.parents for x in (ROOT,i)):raise ValueError('Use new private output outside source and repository')
    release=json.loads((i/'release.json').read_text());cfg=json.loads((i/'dashboard.json').read_text())
    apps=sorted(x['id'] for x in cfg['apps'] if x['id']!='navidrome')
    if 'dns' in apps:raise ValueError('DNS requires separate site-specific setup')
    if subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()!=release['aio_commit']:raise ValueError('Use exact reference release checkout')
    if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip():raise ValueError('Use clean release checkout')
    inventory=inv.collect(i)
    print('Bundle for',','.join(apps),'— exact images and committed source only; no customer data or secrets.')
    if not a.apply:return
    os.umask(0o077);b.mkdir()
    subprocess.run([sys.executable,str(ROOT/'scripts/make-recovery-kit.py'),str(i),'--output',str(b/'kit'),'--apply'],check=True)
    (b/'inventory.json').write_text(json.dumps(inventory))
    subprocess.run(['docker','image','save','-o',str(b/'images.tar.gz'),*sorted({x['id'] for x in inventory['services'].values()})],check=True)
    (b/'bundle.json').write_text(json.dumps({'schema':1,'release':release,'apps':apps,'files':{n:digest(b/n) for n in ('inventory.json','images.tar.gz')}},indent=2))
    check(b,release,apps);print('Bundle verified. Review distribution rights before transferring.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Bundle creation stopped: '+type(e).__name__)
