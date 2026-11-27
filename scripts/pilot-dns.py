#!/usr/bin/env python3
"""Opt-in local Pi-hole pilot. Never alters host DNS, DHCP, router or tailnet DNS."""
import argparse,fcntl,getpass,json,os,re,socket,subprocess,sys
from install import reserve
from pathlib import Path
from private_origins import atomic_write
ROOT=Path(__file__).resolve().parents[1]
def config(i,password):
    if len(password)<12 or len(password)>128 or any(c in password for c in '\n\r\x00$'):raise ValueError('Use a 12–128 character test password without dollar signs or line breaks')
    return {'services':{'pilot-pihole':{'build':{'context':'./security-patches','dockerfile':'Dockerfile.alpine','args':{'BASE_IMAGE':'pihole/pihole:2026.11.0@sha256:66c798d79a95c2691f280329c3611dba1746117c61c9f331907ca35a06a52778','PACKAGE_FLOORS':'libxml2=2.13.9-r3'}},'restart':'unless-stopped','environment':{'TZ':'America/Ciudad_Juarez','FTLCONF_webserver_api_password':password,'FTLCONF_dns_listeningMode':'ALL','FTLCONF_dhcp_active':'false'},'volumes':[str(i/'data/pilot-pihole')+':/etc/pihole'],'ports':['127.0.0.1:18089:80','127.0.0.1:1053:53/tcp','127.0.0.1:1053:53/udp']}}}
def native_config(e,cfg,password,port):
    if not re.fullmatch(r'[A-Za-z0-9_.!@%+\-]{12,128}',password):raise ValueError('Use 12–128 ASCII letters, numbers or ._!@%+-')
    profiles=set(e['COMPOSE_PROFILES'].split(','))
    if 'dns' in profiles or any(x.get('id')=='dns' for x in cfg['apps']):raise ValueError('Existing DNS configuration retained')
    if not 1024<=port<=65535 or port in {int(v) for k,v in e.items() if k.endswith('_PORT') and v.isdigit()}:raise ValueError('Require unused unprivileged DNS port')
    e={**e,'COMPOSE_PROFILES':','.join(sorted(profiles|{'dns'})),'DNS_PASSWORD':password,'DNS_LISTEN_PORT':str(port)}
    cfg={**cfg,'apps':[*cfg['apps'],{'id':'dns','name':'Pi-hole','en':'Network DNS filtering','es':'Filtrado DNS','port':int(e['DNS_WEB_PORT']),'probe':'http://pihole/admin/','path':'/admin/'}]}
    return e,cfg

def native(i,e,password,port):
    pending=i/'.pilot-dns-native-pending'
    data=i/'data/pihole';ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(i)]
    if any((i/n).exists() or (i/n).is_symlink() for n in ('.upgrade-hold.json','.backup-running-services','deployment/recovery-images.json','deployment/pilot-network.json','data/pilot-pihole','.pilot-dns-native-pending')):raise ValueError('Existing DNS or maintenance state; review rather than overwrite')
    cfg=json.loads((i/'dashboard.json').read_text())
    if any(x.get('url') for x in cfg['apps']):raise ValueError('Activate native DNS before enabling private routes')
    new,proposed=native_config(e,cfg,password,port)
    if data.is_symlink() or not data.is_dir() or any(data.iterdir()):raise ValueError('Existing DNS data retained')
    reserve('127.0.0.1',port);reserve('127.0.0.1',port,socket.SOCK_DGRAM)
    reserve('127.0.0.1',int(e['DNS_WEB_PORT']))
    # Private journal blocks backups/updates during incomplete activation.
    # Never remove a newly-created DNS database or reset an existing password.
    pending.mkdir(mode=0o700)
    atomic_write(pending/'env.before',(i/'.env').read_bytes(),0o600)
    atomic_write(pending/'dashboard.before',(i/'dashboard.json').read_bytes(),0o600)
    atomic_write(i/'.env',''.join(k+'='+v+'\n' for k,v in new.items()).encode(),0o600)
    atomic_write(i/'dashboard.json',(json.dumps(proposed,indent=2)+'\n').encode(),0o644)
    subprocess.run(ctl+['config','--quiet'],check=True)
    subprocess.run(ctl+['up','-d','--build','pihole'],check=True)
    subprocess.run(ctl+['up','-d','--force-recreate','--no-deps','--no-build','--pull','never','dashboard'],check=True)
    for p in pending.iterdir():p.unlink()
    pending.rmdir()
    print('Native Pi-hole profile started on loopback; DHCP disabled. Verify DNS and admin before use.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--apply',action='store_true');p.add_argument('--password-stdin',action='store_true',help='Read a single password from the authenticated setup worker');p.add_argument('--native',action='store_true',help='Activate the existing recoverable DNS Compose profile');p.add_argument('--local-port',type=int,default=1053);a=p.parse_args()
    i=a.instance.resolve();e=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or e.get('OWNER_UID')!=str(os.getuid()) or e.get('INSTANCE_DIR')!=str(i) or e.get('BIND_IP')!='127.0.0.1' or (not a.native and i.name!='laptop-test'):raise ValueError('Original isolated pilot operator required')
    overlay=i/'deployment/pilot-network.json';data=i/'data/pilot-pihole'
    if any(x.exists() for x in (overlay,data,i/'.upgrade-hold.json',i/'.backup-running-services',i/'deployment/recovery-images.json')):raise ValueError('Existing DNS or maintenance state; review rather than overwrite')
    port=a.local_port if a.native else 1053
    web=int(e['DNS_WEB_PORT']) if a.native else 18089
    print(f'Pi-hole local pilot: DNS 127.0.0.1:{port} TCP/UDP, admin 127.0.0.1:{web}. DHCP disabled; no network clients changed.')
    if not a.apply:return
    if a.password_stdin:
        if sys.stdin.isatty():raise ValueError('Use a private pipe for password input')
        pw=sys.stdin.read(130).removesuffix('\n')
    else:
        if not sys.stdin.isatty():raise ValueError('Use trusted console')
        pw=getpass.getpass('New Pi-hole admin password: ')
        if pw!=getpass.getpass('Confirm: '):raise ValueError('Password mismatch')
    if not a.native and a.local_port!=1053:raise ValueError('Legacy pilot uses fixed port 1053')
    c=None if a.native else config(i,pw)
    os.umask(0o077)
    with (i/'.backup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.native:
            fresh=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
            if fresh!=e:raise ValueError('Configuration changed during approval')
            native(i,fresh,pw,a.local_port);return
        if overlay.exists() or data.exists():raise ValueError('Existing DNS state')
        data.mkdir(mode=0o700);atomic_write(overlay,json.dumps(c).encode(),0o600)
        ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(i)]
        subprocess.run(ctl+['config','--quiet'],check=True)
        subprocess.run(ctl+['up','-d','--build','pilot-pihole'],check=True)
        print('Local container started; verify DNS before offering it to any client. No router or tailnet DNS changes made.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:sys.exit('DNS pilot stopped: '+type(exc).__name__)
