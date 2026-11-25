"""Initialize only the exact stopped customer Vikunja volume for the pinned non-root image."""
import json,re,subprocess
from pathlib import Path
HELPER='alpine:3.22@sha256:49340b346798875b5592e5d420241f2f9cfba5f47e62ebb1446a1b34734e898f'
def initialize(instance,helper=HELPER,offline=False):
    instance=Path(instance).resolve()
    env=dict(line.split('=',1) for line in (instance/'.env').read_text().splitlines() if '=' in line)
    if 'tasks' not in env['COMPOSE_PROFILES'].split(','):return
    project=env['COMPOSE_PROJECT_NAME']
    if not re.fullmatch(r'jobbi-[a-z0-9-]+',project) or env['INSTANCE_DIR']!=str(instance):raise ValueError('Invalid customer instance')
    volume=project+'_vikunja-files'
    details=json.loads(subprocess.check_output(['docker','volume','inspect',volume],text=True))[0]
    labels=details.get('Labels') or {}
    if details['Name']!=volume or labels.get('com.docker.compose.project')!=project or labels.get('com.docker.compose.volume')!='vikunja-files':
        raise ValueError('Refusing unrelated volume')
    if subprocess.check_output(['docker','ps','-q','--filter','volume='+volume],text=True).strip():
        raise ValueError('Task storage must be stopped before initialization')
    # Only change the mount root. Never recursively chown customer attachments.
    subprocess.run(['docker','run','--rm',*(['--pull','never'] if offline else []),'--network','none','--cap-drop','ALL','--cap-add','CHOWN','--cap-add','DAC_OVERRIDE','--cap-add','FOWNER','--security-opt','no-new-privileges','--mount','type=volume,source='+volume+',target=/files,volume-nocopy',helper,'sh','-ec','chmod 0750 /files; chown 1000:0 /files'],check=True)
