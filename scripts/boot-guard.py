#!/usr/bin/env python3
"""Dedicated appliance only: prevent Docker from starting on missing/replaced storage."""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
def mount(path):
    row=json.loads(subprocess.check_output(['findmnt','--json','--target',str(path),'--output','TARGET,UUID'],text=True))['filesystems']
    if len(row)!=1:raise ValueError('Ambiguous mount')
    target,uuid=row[0]['target'],row[0]['uuid']
    if not uuid or not re.fullmatch(r'[A-Za-z0-9-]+',uuid) or not re.fullmatch(r'/[A-Za-z0-9_./-]*',target):raise ValueError('Require identifiable local filesystem UUID and safe mount path')
    return target,uuid
def unit(mounts):
    checks=sorted(set(mounts))
    return '[Unit]\nRequiresMountsFor='+' '.join(x[0] for x in checks)+'\n[Service]\n' + ''.join('ExecStartPre=/usr/bin/findmnt --noheadings --mountpoint '+p+' --source UUID='+u+'\n' for p,u in checks)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('data',type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
    data=a.data.resolve()
    if not data.is_dir():p.error('Mount data first')
    target,uuid=mount(data)
    if target=='/':p.error('Data must reside on a dedicated mounted filesystem')
    docker=Path(subprocess.check_output(['docker','info','--format','{{.DockerRootDir}}'],text=True).strip())
    if not docker.is_dir():p.error('Cannot inspect Docker root')
    body=unit([(target,uuid),mount(docker)])
    print(body)
    if not a.apply:return
    if os.geteuid()!=0:p.error('Use sudo only on the dedicated customer host')
    if subprocess.check_output(['docker','ps','-aq'],text=True).strip():p.error('Boot guard must be installed before any containers exist; do not alter shared Docker hosts')
    d=Path('/etc/systemd/system/docker.service.d');d.mkdir(mode=0o755,exist_ok=True)
    path=d/'90-jobbi-storage.conf'
    if path.exists() and path.read_text()!=body:p.error('Existing guard differs; review manually')
    if not path.exists():
        with path.open('x') as out:out.write(body)
        path.chmod(0o644)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','docker'],check=True)
    print('Guard installed. Existing daemon is not restarted; verify reboot on dedicated hardware.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:sys.exit('Boot guard stopped: '+str(e))
