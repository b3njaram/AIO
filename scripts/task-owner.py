#!/usr/bin/env python3
"""Create the first Vikunja owner using its local CLI, with registration closed."""
import argparse,getpass,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('username');p.add_argument('email');a=p.parse_args()
    i=a.instance.resolve()
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if env.get('INSTANCE_DIR')!=str(i) or 'tasks' not in env.get('COMPOSE_PROFILES','').split(',') or env.get('TASK_REGISTRATION')!='false':p.error('Use a new tasks-enabled instance with closed registration')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,48}',a.username) or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',a.email):p.error('Invalid username/email')
    pw=getpass.getpass('New Vikunja password (12+ characters): ')
    if len(pw)<12 or pw!=getpass.getpass('Confirm password: '):p.error('Password too short or mismatch')
    # The pinned Vikunja CLI accepts password as an argument: trusted local Docker admins can see it transiently.
    subprocess.run(['bash',str(ROOT/'scripts/ctl.sh'),str(i),'exec','-T','vikunja','/app/vikunja/vikunja','user','create','--username',a.username,'--email',a.email,'--password',pw],check=True)
    print('User created with public registration disabled. Verify login privately.')
if __name__=='__main__':main()
