#!/usr/bin/env python3
"""One-command private handoff pack; no credentials or implied acceptance."""
import argparse,datetime as dt,importlib.util,json,os,re,sys
from pathlib import Path
from offline_kit import digest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('delivery',ROOT/'scripts/customer-delivery.py');delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery)
def build(i,out):
    release=json.loads((i/'release.json').read_text());config=json.loads((i/'dashboard.json').read_text())
    en=delivery.guide(config,release,'en');es=delivery.guide(config,release,'es')
    names=sorted({a['id'] for a in config['apps']})
    checklist={'schema':1,'release':release['aio_commit'],'apps':{a:'pending' for a in names},'checks':{x:'pending' for x in ('storage_identity','independent_restore','physical_reboot','private_tls','customer_accounts','warranty_and_receipt','support_and_privacy','installer_access_removed')},'approved':False}
    os.umask(0o077);out.mkdir(mode=0o700)
    for name,body in [('START-HERE-en.md',en),('EMPIEZA-AQUI-es.md',es),('acceptance-draft.json',json.dumps(checklist,indent=2)+'\n'),('TECHNICIAN.md','''# Technician handoff
Review the bilingual guides and verify all private addresses. No password or recovery key belongs in this pack. Complete customer-controlled accounts, private access and application-specific functional checks. Use the documented USB installer and independent recovery kit as applicable. Review storage mounts, backup recovery, physical power behavior and actual support/warranty terms. Attach the actual transaction-specific documents from the private business dashboard separately. Do not mark a pending or deferred test as passed. This draft is not a commercial approval.
''')]:
        with (out/name).open('x') as f:f.write(body)
    with (out/'manifest.json').open('x') as f:json.dump({'schema':1,'release':release['aio_commit'],'generated':dt.datetime.now(dt.timezone.utc).isoformat(),'files':{x.name:digest(x) for x in out.iterdir() if x.name!='manifest.json'}},f,indent=2)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    i=a.instance.resolve();out=a.output.expanduser().absolute();parent=out.parent.resolve()
    if out.exists() or out.is_symlink() or not parent.is_dir() or any(x==parent or x in parent.parents for x in (i,ROOT)):raise ValueError('New private output directory outside instance and Git required')
    release=json.loads((i/'release.json').read_text());config=json.loads((i/'dashboard.json').read_text())
    delivery.guide(config,release,'en')
    print('Prepare two language guides, blank acceptance record, technician instructions and checksums. No credentials.')
    if a.apply:build(i,out);print('Private draft pack created. Verify all contents before delivery.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError) as e:sys.exit('Handoff stopped: '+type(e).__name__)
