#!/usr/bin/env python3
"""Restore the mandatory existing launcher after boot, without recreating services."""
import argparse,fcntl,os,subprocess,sys,time,urllib.request
from pathlib import Path
from backup_mount import mount_identity
ROOT=Path(__file__).resolve().parents[1]

def recover(instance,expected_mount,run=subprocess.run,ready=None):
    i=instance.resolve()
    if mount_identity(i)!=expected_mount:raise ValueError('Approved data filesystem unavailable')
    e=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or e.get('OWNER_UID')!=str(os.getuid()) or e.get('INSTANCE_DIR')!=str(i) or e.get('COMPOSE_PROJECT_NAME')!='jobbi-'+i.name:
        raise ValueError('Original instance operator required')
    with (i/'.backup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (i/'.upgrade-hold.json').exists():
            print('Source held for update; launcher recovery skipped');return
        if (i/'.backup-running-services').exists():raise ValueError('Interrupted backup must resume before launcher recovery')
        port=int(e['DASH_PORT'])
        if not 1024<=port<=65535:raise ValueError('Invalid dashboard port')
        ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(i)]
        if ready is None:
            def ready():
                try:
                    with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/healthz',timeout=4) as response:return response.status==200
                except OSError:return False
        # Start only the already-created mandatory dashboard, not any removed app.
        # No Compose up, build, pull, volume creation or image substitution.
        for attempt in range(3):
            if ready():return
            run([*ctl,'start','dashboard'],check=True,timeout=90)
            for _ in range(15):
                if ready():return
                time.sleep(2)
        raise ValueError('Existing dashboard did not become reachable after boot')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--expected-mount',required=True);a=p.parse_args()
    recover(a.instance,a.expected_mount)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Boot recovery stopped: '+str(e))
