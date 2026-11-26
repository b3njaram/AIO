#!/usr/bin/env python3
"""Remove and reinstall all containers in a recovered CI fixture; verify volumes and image IDs."""
import json
import os
from pathlib import Path
import subprocess
import sys

def run(*args):
    return subprocess.check_output(args,text=True).strip()

def main():
    instance=Path(sys.argv[1]).resolve()
    if os.getenv('GITHUB_ACTIONS')!='true' or instance not in [Path('/tmp/jobbi-'+name+'/recovered') for name in ('library','office','media','infra')]:
        raise ValueError('Disposable recovered CI project required')
    env=dict(row.split('=',1) for row in (instance/'.env').read_text().splitlines() if '=' in row)
    if env['INSTANCE_DIR']!=str(instance) or env['COMPOSE_PROJECT_NAME']!='jobbi-recovered' or env['BIND_IP']!='127.0.0.1':
        raise ValueError('Wrong CI project')
    ctl=['bash',str(Path(__file__).with_name('ctl.sh')),str(instance)]
    def snapshot():
        ids=run(*ctl,'ps','-aq').split()
        if not ids:raise ValueError('Missing CI containers')
        entries={}
        for cid in ids:
            # Never log inspect output, which can include test credentials.
            info=json.loads(run('docker','inspect',cid))[0]
            service=info['Config']['Labels']['com.docker.compose.service']
            mounts=sorted((m['Type'],m['Destination'],m.get('Name',m['Source'])) for m in info['Mounts'] if m['Type'] in ('bind','volume'))
            entries[service]=(info['Image'],mounts)
        return entries
    before=snapshot()
    run(*ctl,'stop')
    run(*ctl,'rm','--force')
    if run(*ctl,'ps','-aq'):raise AssertionError('Uninstall left containers in the disposable project')
    run(*ctl,'create','--no-build','--pull','never')
    if before!=snapshot():raise AssertionError('Reinstalled services, mount identities or images differ')
    run(*ctl,'start')
    print('Reinstalled',len(before),'services using retained storage and exact image identities')

if __name__=='__main__':main()
