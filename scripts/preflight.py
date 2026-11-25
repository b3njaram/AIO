#!/usr/bin/env python3
"""Read-only capacity and environment check; never formats disks or alters Docker."""
import argparse, json, os, platform, shutil, subprocess, sys
from pathlib import Path
def gib(n): return round(n/1024**3,1)
def cmd(*args): return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT).strip()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root',required=True,type=Path)
    p.add_argument('--apps',default='music,movies,photos,files,passwords,tasks,monitor,remote')
    p.add_argument('--minimum-free-gib',type=float,default=50)
    a=p.parse_args()
    apps=set(filter(None,a.apps.split(',')))
    if apps-set('music movies photos files passwords tasks dns monitor remote'.split()): p.error('Unknown app')
    if a.minimum_free_gib<0: p.error('Invalid free-space target')
    root=a.data_root.expanduser().resolve()
    if not root.is_dir(): p.error('Create/mount intended data root first')
    errors=[]; warnings=[]
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','AMD64'): errors.append('Pilot supported target is x86-64 Linux only')
    for exe in ('docker','git','bash','curl'):
        if not shutil.which(exe): errors.append('Missing '+exe)
    disk=shutil.disk_usage(root)
    if gib(disk.free)<a.minimum_free_gib: errors.append('Insufficient data disk free space')
    if not os.access(root,os.W_OK|os.X_OK): errors.append('Data root is not writable')
    mem=None
    try: mem=gib(int(next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')).split()[1])*1024)
    except (OSError,StopIteration,ValueError): warnings.append('Cannot measure host RAM')
    ram_target=16 if 'photos' in apps or len(apps)>=5 else 8
    if mem is not None and mem<ram_target*.9: warnings.append(f'Below proposed {ram_target} GiB RAM target; validate workload before sale')
    docker_root=None; docker_free=None
    try:
        docker_root=cmd('docker','info','--format','{{.DockerRootDir}}')
        cmd('docker','compose','version')
        if Path(docker_root).is_dir():
            docker_free=gib(shutil.disk_usage(docker_root).free)
            if docker_free<20: errors.append('Docker filesystem below 20 GiB free')
        else: warnings.append('Docker data filesystem not locally inspectable')
    except (OSError,subprocess.CalledProcessError): errors.append('Docker daemon or Compose unavailable')
    if not root.is_mount(): warnings.append('Data root is not itself a mount point; verify intended disk and reboot persistence')
    warnings.append('Manual checks required: SMART, redundancy, backup destination, network/ports, HTTPS, actual workload and wall power.')
    print(json.dumps({'data_root':str(root),'data_free_gib':gib(disk.free),'docker_root':docker_root,'docker_free_gib':docker_free,'ram_gib':mem,'ram_target_gib':ram_target,'errors':errors,'warnings':warnings},indent=2))
    return bool(errors)
if __name__=='__main__': sys.exit(main())
