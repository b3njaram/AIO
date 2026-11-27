#!/usr/bin/env python3
"""Apply a dashboard-only pilot overlay; never changes release metadata or application volumes."""
import json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASELINES={'8e777404ee151410bd02681fe87c307c861d8d50','49dc18cce65216b354212c790b3074b7d9da90dc'}
def main():
    if os.geteuid()==0 or len(sys.argv)!=2:raise ValueError('Use original non-root operator and instance path')
    i=Path(sys.argv[1]).resolve()
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if env.get('INSTANCE_DIR')!=str(i) or env.get('OWNER_UID')!=str(os.getuid()) or env.get('BIND_IP')!='127.0.0.1':raise ValueError('Require original isolated pilot')
    baseline=json.loads((i/'release.json').read_text())['aio_commit']
    if baseline not in BASELINES:raise ValueError('Overlay applies only to tested laptop baseline')
    if any((i/p).exists() for p in ('.upgrade-hold.json','.backup-running-services','deployment/recovery-images.json')):raise ValueError('Active recovery or backup; stop')
    dest=i/'deployment/dashboard';source=ROOT/'deploy/dashboard'
    if not dest.is_dir() or dest.is_symlink():raise ValueError('Missing frozen dashboard')
    files=('index.html','server.py','home.svg','manifest.webmanifest')
    if any(not (dest/f).is_file() or (dest/f).is_symlink() for f in files):raise ValueError('Unsafe dashboard files')
    rev=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    marker=i/'pilot-dashboard-overlay.json'
    if marker.exists() and json.loads(marker.read_text()).get('commit')==rev:
        print('Overlay already applied');return
    backup=Path(tempfile.mkdtemp(prefix='dashboard-before-pilot-',dir=i))
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(i)]
    for f in files:shutil.copy2(dest/f,backup/f)
    try:
        for f in files:shutil.copy2(source/f,dest/f)
        subprocess.run(ctl+['up','-d','--no-deps','--build','--force-recreate','dashboard'],check=True)
        import urllib.request
        port=int(env['DASH_PORT'])
        for attempt in range(30):
            try:
                with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/',timeout=3) as response:
                    if response.read()==(source/'index.html').read_bytes():break
            except OSError:pass
            import time;time.sleep(1)
        else:raise ValueError('Running dashboard did not serve the exact updated HTML')
        marker.write_text(json.dumps({'commit':rev,'baseline':baseline,'scope':'dashboard only','previous_files':backup.name})+'\n')
        print('Dashboard overlay applied; exact release image certification no longer applies. Previous dashboard files:',backup)
    except BaseException:
        for f in files:shutil.copy2(backup/f,dest/f)
        print('Previous files restored; rebuild dashboard with ctl.sh if required.',file=sys.stderr)
        raise
if __name__=='__main__':main()
