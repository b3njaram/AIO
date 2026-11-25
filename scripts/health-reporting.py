#!/usr/bin/env python3
"""Opt-in customer-to-owner private health reporting. No remote commands or polling."""
import argparse,getpass,importlib.util,json,os,re,sys,ssl,fcntl,urllib.parse
from pathlib import Path
from maintenance_alerts import PrivateHTTPS,atomic,private_read
spec=importlib.util.spec_from_file_location('share',Path(__file__).with_name('share-health.py'));share=importlib.util.module_from_spec(spec);spec.loader.exec_module(share)
def endpoint(value):
    u=urllib.parse.urlsplit(value)
    if u.scheme!='https' or not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+\.ts\.net',u.hostname or '') or u.username or u.password or u.query or u.fragment or u.path!='/v1/health' or u.port!=17993 or u.netloc!=u.hostname+':17993':raise ValueError('Use exact private HTTPS reporting endpoint on port 17993')
    return u
def send(cfg,i):
    if set(cfg)!={'url','token','id'} or not re.fullmatch(r'[A-Za-z0-9_-]{43}',cfg['token']):raise ValueError('Invalid reporting credential')
    u=endpoint(cfg['url']);report=share.report(i,cfg['id'])
    c=PrivateHTTPS(u.hostname,u.port,timeout=10,context=ssl.create_default_context())
    try:
        c.request('POST',u.path,body=json.dumps(report).encode(),headers={'Authorization':'Bearer '+cfg['token'],'Content-Type':'application/json'})
        with c.getresponse() as r:
            if r.status!=200:raise ValueError('Report not accepted; verify consent, expiry and freshness')
    finally:c.close()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('action',choices=['enable','disable','send','status']);p.add_argument('--url');p.add_argument('--appliance-id');p.add_argument('--apply',action='store_true');a=p.parse_args()
    i=a.instance.resolve();env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or env.get('INSTANCE_DIR')!=str(i) or env.get('OWNER_UID')!=str(os.getuid()):p.error('Original non-root operator required')
    os.umask(0o077);path=i/'.health-reporting.json'
    with (i/'.health-reporting.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if a.action=='status':print('Configured' if path.is_file() else 'Disabled');return
        if a.action=='disable':
            if a.apply:path.unlink(missing_ok=True);print('Disabled; ask owner to revoke the credential too.')
            else:print('Preview only; --apply removes the local credential.')
            return
        if a.action=='enable':
            if not a.url or not a.appliance_id:p.error('Approved endpoint and appliance ID required')
            endpoint(a.url);share.report(i,a.appliance_id)
            if not a.apply:print('Preview only: send the same sanitized report as manual sharing every 15 minutes after explicit opt-in.');return
            if not sys.stdin.isatty():p.error('Use a trusted interactive terminal')
            token=getpass.getpass('Reporting credential: ')
            if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):p.error('Invalid credential')
            atomic(path,{'url':a.url,'token':token,'id':a.appliance_id});print('Configured. Check delivery manually and enable reviewed timer.')
            return
        if not path.exists():print('Disabled');return
        send(private_read(path,os.getuid()),i);print('Private health report accepted.')
if __name__=='__main__':
    try:main()
    except Exception as e:sys.exit('Reporting unavailable: '+type(e).__name__)
