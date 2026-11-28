#!/usr/bin/env python3
"""Link and verify this instance's Prowlarr key; no external account provisioning."""
import argparse
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from private_origins import atomic_write

ROOT = Path(__file__).resolve().parents[1]
KEY = re.compile(r'[A-Za-z0-9]{24,128}')
VERIFY = """
const base = 'http://prowlarr:9696';
const key = process.env.PROWLARR_API_KEY;
if (!key || process.env.PROWLARR_URL !== base) process.exit(1);
try {
  const r = await fetch(base + '/api/v1/system/status', {
    headers: {'X-Api-Key': key}, redirect: 'manual',
    signal: AbortSignal.timeout(5000)
  });
  if (!r.ok || (await r.json()).appName !== 'Prowlarr') process.exit(1);
} catch { process.exit(1); }
"""

def link(instance, *, run=subprocess.run, sleep=time.sleep):
    instance = instance.resolve()
    env = instance / '.env'
    lines = env.read_text().splitlines(keepends=True)
    settings = dict(line.rstrip('\r\n').split('=', 1) for line in lines
                    if '=' in line and not line.startswith('#'))
    if (settings.get('INSTANCE_DIR') != str(instance)
            or not re.fullmatch(r'jobbi-[a-z0-9-]+', settings.get('COMPOSE_PROJECT_NAME', ''))
            or settings.get('OWNER_UID') != str(os.getuid())
            or os.geteuid() == 0 or settings.get('BIND_IP') != '127.0.0.1'
            or 'movies' not in settings.get('COMPOSE_PROFILES', '').split(',')):
        raise ValueError('Original isolated movie instance operator required')
    slots = [n for n, line in enumerate(lines) if line.startswith('PROWLARR_API_KEY=')]
    if len(slots) != 1 or env.is_symlink():
        raise ValueError('Invalid instance key configuration')
    if any((instance / n).exists() for n in
           ('.upgrade-hold.json', '.backup-running-services', '.private-origins')):
        raise ValueError('Maintenance or origin transaction active')
    config = instance / 'data/prowlarr/config.xml'
    key = ''
    for attempt in range(20):
        try:
            if config.is_symlink() or config.stat().st_size > 65536:
                raise ValueError('Invalid local Prowlarr configuration')
            key = ET.parse(config).getroot().findtext('ApiKey', '').strip()
        except (OSError, ET.ParseError):
            key = ''
        if KEY.fullmatch(key):
            break
        if attempt < 19:
            sleep(3)
    else:
        raise ValueError('Local Prowlarr key unavailable')
    current = settings.get('PROWLARR_API_KEY', '')
    if current and current != key:
        raise ValueError('Existing Prowlarr key differs; review locally')
    ctl = ['bash', str(ROOT / 'scripts/ctl.sh'), str(instance)]
    quiet = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    probe = ctl + ['exec', '-T', 'backend', 'node', '--input-type=module', '-e', VERIFY]
    def ready():
        return run(probe, timeout=20, **quiet).returncode == 0
    if current == key and ready():
        return
    if not current:
        lines[slots[0]] = 'PROWLARR_API_KEY=' + key + '\n'
        atomic_write(env, ''.join(lines).encode(), 0o600)
    # Reconcile an interrupted first attempt with the same retained key.
    run(ctl + ['up', '-d', '--no-build', 'backend'], check=True, timeout=180, **quiet)
    for attempt in range(15):
        if ready():
            return
        if attempt < 14:
            sleep(3)
    raise ValueError('Prowlarr connection not yet authenticated; retained key for retry')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('instance', type=Path)
    a = p.parse_args()
    link(a.instance)
    print('Local Prowlarr API authenticated from StreamHub. Indexers remain customer-managed.')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError):
        sys.exit('Prowlarr connection needs review; no credentials printed.')
