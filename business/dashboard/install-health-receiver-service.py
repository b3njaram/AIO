#!/usr/bin/env python3
"""Preview/install a dedicated owner user service for private health reporting."""
import argparse,os,re,subprocess,sys
from pathlib import Path
def safe(value):
    p=Path(value).expanduser().resolve()
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(p)):raise ValueError('Use reviewed absolute paths without spaces')
    return str(p)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cert',required=True,type=Path);p.add_argument('--key',required=True,type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
    if os.geteuid()==0:p.error('Run as the owner, not root')
    executable=safe(sys.executable);script=safe(Path(__file__).with_name('health-receiver.py'));cert=safe(a.cert);key=safe(a.key)
    for x in (cert,key):
        path=Path(x)
        if not path.is_file() or path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o022:raise ValueError('Review TLS file ownership and permissions')
    if Path(key).stat().st_mode&0o077:raise ValueError('Private key must be mode 0600')
    body='[Unit]\nDescription=Optional JobbiSoft private health receiver\n[Service]\nType=simple\nUMask=0077\nNoNewPrivileges=true\nExecStart='+executable+' '+script+' --cert '+cert+' --key '+key+' --apply\nRestart=on-failure\nRestartSec=30s\n[Install]\nWantedBy=default.target\n'
    print(body)
    if not a.apply:return
    d=Path.home()/'.config/systemd/user';d.mkdir(mode=0o700,parents=True,exist_ok=True)
    target=d/'jobbi-health-receiver.service'
    if target.is_symlink() or target.exists() and target.read_text()!=body:raise ValueError('Existing unit differs; review manually')
    if not target.exists():
        with target.open('x') as out:out.write(body)
        target.chmod(0o600)
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    subprocess.run(['systemctl','--user','enable','--now',target.name],check=True)
    print('Service enabled; verify status and tailnet ACL. If needed, separately authorize user lingering to survive logout/reboot.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.SubprocessError) as e:sys.exit('Service setup refused: '+type(e).__name__)
