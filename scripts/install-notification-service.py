#!/usr/bin/env python3
"""Opt-in non-root notification timer. No changes to existing application services."""
import argparse,os,pwd,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def units(i,user):
    root=str(ROOT);python=sys.executable
    if not all(re.fullmatch(r'/[A-Za-z0-9_./-]+',x) for x in (str(i),root,python)):raise ValueError('Unsafe path')
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,35}',i.name) or not re.fullmatch('[a-z_][a-z0-9_-]*',user) or env.get('INSTANCE_DIR')!=str(i) or env.get('OWNER_UID')!=str(pwd.getpwnam(user).pw_uid) or pwd.getpwnam(user).pw_uid==0:raise ValueError('Original non-root owner required')
    name='jobbi-'+i.name+'-notifications'
    service='[Unit]\nDescription=Customer-approved maintenance notification check\nRequiresMountsFor='+str(i)+'\nConditionPathExists='+str(i/'.notification-config.json')+'\n[Service]\nType=oneshot\nUser='+user+'\nUMask=0077\nNoNewPrivileges=true\nExecStart='+python+' '+root+'/scripts/notifications.py '+str(i)+' check\n'
    timer='[Unit]\nDescription=Check maintenance notifications\n[Timer]\nOnBootSec=3min\nOnUnitActiveSec=15min\nUnit='+name+'.service\n[Install]\nWantedBy=timers.target\n'
    return {name+'.service':service,name+'.timer':timer}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--operator',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    result=units(a.instance.resolve(),a.operator)
    for name,body in result.items():print(name+'\n'+body)
    if not a.apply:return
    if os.geteuid()!=0:p.error('Use sudo only on the dedicated appliance')
    for name,body in result.items():
        path=Path('/etc/systemd/system')/name
        if path.is_symlink() or path.exists() and path.read_text()!=body:raise ValueError('Existing unit differs')
    for name,body in result.items():
        path=Path('/etc/systemd/system')/name
        if not path.exists():
            with path.open('x') as out:out.write(body)
            path.chmod(0o644)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now',*[x for x in result if x.endswith('.timer')]],check=True)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Notification timer stopped: '+type(e).__name__)
