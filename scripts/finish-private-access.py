#!/usr/bin/env python3
"""Apply or roll back approved private routes and selected application origins."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--https-base',type=int,default=19443);mode=p.add_mutually_exclusive_group();mode.add_argument('--apply',action='store_true',help='Customer approved local accounts, ACL policy, Vaultwarden invitation and service interruption');mode.add_argument('--rollback',action='store_true');a=p.parse_args()
    i=a.instance.resolve()
    apps={x['id'] for x in json.loads((i/'dashboard.json').read_text())['apps']}
    services=['dashboard']+[v for k,v in [('music','jobbi-music'),('movies','backend'),('passwords','vaultwarden'),('tasks','vikunja')] if k in apps]
    access=[sys.executable,str(ROOT/'scripts/private-access.py'),str(i),'--https-base',str(a.https_base)]
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(i),'up','-d','--force-recreate','--no-deps','--no-build','--pull','never',*services]
    def run(command):subprocess.run(command,check=True)
    def undo():
        if (i/'.private-serve.json').exists():run(access+['--rollback-routes'])
        if (i/'.private-origins').exists():
            run(access+['--rollback-origins']);run(ctl)
    if a.rollback:undo();return
    if not a.apply:run(access);print('Preview only; add --apply after customer approves ACLs and onboarding.');return
    if any((i/n).exists() for n in ('.private-serve.json','.private-origins','.nextcloud-origin.json')):raise ValueError('Prior private-access transaction exists; review or roll back')
    run(access)
    try:
        run(access+['--prepare-origins']);run(ctl);run(access+['--enable-routes']);run(access+['--verify'])
    except (OSError,subprocess.CalledProcessError):
        print('Private setup failed; attempting rollback of this transaction only.',file=sys.stderr)
        undo()
        raise
    print('Private HTTPS configuration verified locally; test actual TLS, ACL denial and app logins from a second customer device.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:sys.exit('Private setup stopped: '+str(e))
