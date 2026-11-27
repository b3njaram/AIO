"""Exercise the Prowlarr API from the disposable StreamHub backend and verify restore."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/tmp/jobbi-media/source')
RECOVERED = SOURCE.with_name('recovered')
FINGERPRINT = SOURCE.parent / 'prowlarr-key.fingerprint'
CHECK_API = """
let key = '';
for await (const chunk of process.stdin) key += chunk;
const base = process.env.PROWLARR_URL;
if (base !== 'http://prowlarr:9696') process.exit(1);
try {
  const get = (path, headers) => fetch(base + path, {
    headers, redirect: 'manual', signal: AbortSignal.timeout(5000)
  });
  const denied = await get('/api/v1/system/status', {});
  if (![401, 403].includes(denied.status)) process.exit(1);
  const headers = {'X-Api-Key': key};
  const status = await get('/api/v1/system/status', headers);
  const indexers = await get('/api/v1/indexer', headers);
  if (!status.ok || !indexers.ok) process.exit(1);
  const system = await status.json();
  const items = await indexers.json();
  if (system.appName !== 'Prowlarr' || !system.version || !Array.isArray(items)) process.exit(1);
} catch {
  process.exit(1);
}
"""


def main():
    instance = Path(sys.argv[1]).resolve()
    if os.getenv('GITHUB_ACTIONS') != 'true' or instance not in (SOURCE, RECOVERED):
        raise ValueError('Disposable media CI only')
    ctl = ['bash', str(ROOT / 'scripts/ctl.sh'), str(instance)]
    for _ in range(30):
        try:
            key = ET.parse(instance / 'data/prowlarr/config.xml').getroot().findtext('ApiKey', '')
        except (OSError, ET.ParseError):
            key = ''
        if re.fullmatch(r'[A-Za-z0-9]{24,128}', key):
            result = subprocess.run([
                *ctl, 'exec', '-T', 'backend', 'node', '--input-type=module', '-e', CHECK_API
            ], input=key, text=True, capture_output=True, timeout=25)
            if result.returncode == 0:
                break
        time.sleep(3)
    else:
        raise RuntimeError('Prowlarr authenticated status or indexer listing failed from StreamHub')
    fingerprint = hashlib.sha256(key.encode()).hexdigest()
    if instance == SOURCE:
        with os.fdopen(os.open(FINGERPRINT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            stream.write(fingerprint)
    elif FINGERPRINT.read_text() != fingerprint:
        raise RuntimeError('Prowlarr API credential was not retained in restore')
    print('PASS: StreamHub-to-Prowlarr routing, API authentication, and local indexer listing')


if __name__ == '__main__':
    main()
