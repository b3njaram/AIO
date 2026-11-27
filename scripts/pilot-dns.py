#!/usr/bin/env python3
"""Opt-in local Pi-hole pilot. Never alters host DNS, DHCP, router or tailnet DNS."""
import argparse,fcntl,getpass,json,os,subprocess,sys
from pathlib import Path
from private_origins import atomic_write
ROOT=Path(__file__).resolve().parents[1]
def config(i,password):
    if len(password)<12 or len(password)>128 or any(c in password for c in '\n\r\x00$'):raise ValueError('Use a 12–128 character test password without dollar signs or line breaks')
    return {'services':{'pilot-pihole':{'build':{'context':'./security-patches','dockerfile':'Dockerfile.alpine','args':{'BASE_IMAGE':'pihole/pihole:2026.11.0@sha256:66c798d79a95c2691f280329c3611dba1746117c61c9f331907ca35a06a52778','PACKAGE_FLOORS':'libxml2=2.13.9-r3'}},'restart':'unless-stopped','environment':{'TZ':'America/Ciudad_Juarez','FTLCONF_webserver_api_password':password,'FTLCONF_dns_listeningMode':'ALL','FTLCONF_dhcp_active':'false'},'volumes':[str(i/'data/pilot-pihole')+':/etc/pihole'],'ports':['127.0.0.1:18089:80','127.0.0.1:1053:53/tcp','127.0.0.1:1053:53/udp']}}}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--apply',action='store_true');p.add_argument('--password-stdin',action='store_true',help='Read a single password from the authenticated setup worker');a=p.parse_args()
    i=a.instance.resolve();e=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or e.get('OWNER_UID')!=str(os.getuid()) or e.get('INSTANCE_DIR')!=str(i) or e.get('BIND_IP')!='127.0.0.1' or i.name!='laptop-test':raise ValueError('Original isolated pilot operator required')
    overlay=i/'deployment/pilot-network.json';data=i/'data/pilot-pihole'
    if any(x.exists() for x in (overlay,data,i/'.upgrade-hold.json',i/'.backup-running-services',i/'deployment/recovery-images.json')):raise ValueError('Existing DNS or maintenance state; review rather than overwrite')
    print('Pi-hole local pilot: DNS 127.0.0.1:1053 TCP/UDP, admin 127.0.0.1:18089. DHCP disabled; no network clients changed.')
    if not a.apply:return
    if a.password_stdin:
        if sys.stdin.isatty():raise ValueError('Use a private pipe for password input')
        pw=sys.stdin.read(130).removesuffix('\n')
    else:
        if not sys.stdin.isatty():raise ValueError('Use trusted console')
        pw=getpass.getpass('New Pi-hole admin password: ')
        if pw!=getpass.getpass('Confirm: '):raise ValueError('Password mismatch')
    c=config(i,pw)
    os.umask(0o077)
    with (i/'.backup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if overlay.exists() or data.exists():raise ValueError('Existing DNS state')
        data.mkdir(mode=0o700);atomic_write(overlay,json.dumps(c).encode(),0o600)
        ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(i)]
        subprocess.run(ctl+['config','--quiet'],check=True)
        subprocess.run(ctl+['up','-d','--build','pilot-pihole'],check=True)
        print('Local container started; verify DNS before offering it to any client. No router or tailnet DNS changes made.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:sys.exit('DNS pilot stopped: '+type(exc).__name__)
