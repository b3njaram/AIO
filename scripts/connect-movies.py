#!/usr/bin/env python3
"""Link this instance's own Prowlarr API key; no third-party account provisioning."""
import argparse, os, re, subprocess, tempfile, xml.etree.ElementTree as ET
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('instance',type=Path)
a=p.parse_args()
instance=a.instance.resolve()
env=instance/'.env'
lines=env.read_text().splitlines()
settings=dict(line.split('=',1) for line in lines if '=' in line and not line.startswith('#'))
if settings.get('INSTANCE_DIR')!=str(instance) or not re.fullmatch(r'jobbi-[a-z0-9-]+',settings.get('COMPOSE_PROJECT_NAME','')):
    p.error('Not an AIO instance')
if 'movies' not in settings.get('COMPOSE_PROFILES','').split(','): p.error('Movies are not selected')
key=ET.parse(instance/'data/prowlarr/config.xml').getroot().findtext('ApiKey','').strip()
if not re.fullmatch(r'[A-Za-z0-9]{16,128}',key): p.error('Local Prowlarr API key unavailable; finish first-run setup')
with tempfile.NamedTemporaryFile(mode='w',dir=instance,delete=False) as tmp:
    tmp.write('\n'.join('PROWLARR_API_KEY='+key if line.startswith('PROWLARR_API_KEY=') else line for line in lines)+'\n')
    name=tmp.name
os.chmod(name,0o600)
os.replace(name,env)
subprocess.run(['bash',str(Path(__file__).resolve().parent/'ctl.sh'),str(instance),'up','-d','backend','frontend'],check=True)
print('Local internal key linked. External integrations remain customer-managed.')
