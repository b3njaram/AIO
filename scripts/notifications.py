#!/usr/bin/env python3
"""Configure customer-owned ntfy-compatible private notification delivery."""
import argparse,getpass,json,os,sys,fcntl
from pathlib import Path
from maintenance_alerts import private_url,atomic,process,private_read
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('action',choices=['status','enable','disable','check']);p.add_argument('--url');p.add_argument('--apply',action='store_true');a=p.parse_args()
    i=a.instance.resolve();env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or env.get('INSTANCE_DIR')!=str(i) or env.get('OWNER_UID')!=str(os.getuid()):p.error('Run as original non-root appliance operator')
    os.umask(0o077);config=i/'.notification-config.json';state=i/'.notification-state.json'
    if a.action=='status':
        print('Private notifications configured' if config.is_file() else 'Private notifications disabled');return
    if a.action=='enable':
        if not a.url:p.error('Provide customer-approved private topic URL')
        private_url(a.url)
        if not a.apply:print('Preview: fixed alert categories only, no credentials or personal files. Add --apply to approve.');return
        if not sys.stdin.isatty():p.error('Use a trusted interactive terminal')
        token=getpass.getpass('Private notification access token: ')
        import re
        if not re.fullmatch(r'[A-Za-z0-9_.~-]{16,512}',token):p.error('Invalid access token')
        with (i/'.notification.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            atomic(config,{'url':a.url,'token':token,'enabled':True});state.unlink(missing_ok=True)
        print('Enabled. Verify the private destination and its access controls.')
    elif a.action=='disable':
        if not a.apply:print('Preview: add --apply to erase local notification credentials');return
        with (i/'.notification.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            config.unlink(missing_ok=True);state.unlink(missing_ok=True)
        print('Disabled; revoke the token on the destination too.')
    else:
        try:s=json.loads((i/'data/.dashboard-metrics/health.json').read_text())
        except (OSError,ValueError):s={}
        print(json.dumps(process(i,s),indent=2))
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError) as e:sys.exit('Notification operation stopped: '+type(e).__name__)
