#!/usr/bin/env python3
"""Approve read-only monitoring of a local existing NUT UPS."""
import argparse,json,os,re,sys,subprocess
from pathlib import Path
from power_management import snapshot,parse
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('action',choices=['status','configure','disable']);p.add_argument('--ups');p.add_argument('--apply',action='store_true');a=p.parse_args()
    i=a.instance.resolve();env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or env.get('OWNER_UID')!=str(os.getuid()) or env.get('INSTANCE_DIR')!=str(i):p.error('Original non-root operator required')
    path=i/'.ups-name'
    if a.action=='status':print(json.dumps(snapshot(i),indent=2));return
    if a.action=='disable':
        if a.apply:path.unlink(missing_ok=True)
        print('UPS dashboard monitoring disabled' if a.apply else 'Preview only. Native NUT protection unchanged.');return
    if not a.ups or not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',a.ups):p.error('Specify an existing local NUT UPS name')
    status=parse(subprocess.check_output(['upsc',a.ups+'@127.0.0.1'],text=True,stderr=subprocess.DEVNULL,timeout=5))
    if status['state']=='unknown':p.error('UPS status unavailable')
    print(json.dumps(status,indent=2))
    if not a.apply:print('Preview only; no native shutdown configured.');return
    os.umask(0o077)
    with path.open('x') as out:out.write(a.ups+'\n')
    print('Monitoring enabled; verify native NUT shutdown independently.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('UPS setup stopped: '+type(e).__name__)
