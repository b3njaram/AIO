"""Instance-local transaction for the HTTPS origin and dashboard files."""
import hashlib
import json
import os
import tempfile
from pathlib import Path


def atomic_write(path, data, mode):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        try:
            tmp.write(data)
            tmp.flush()
            os.fchmod(tmp.fileno(), mode)
            os.fsync(tmp.fileno())
            os.replace(tmp.name, path)
        finally:
            Path(tmp.name).unlink(missing_ok=True)


def desired(i, config, updates):
    original=(i/'.env').read_text().splitlines(keepends=True)
    seen=set()
    for idx,line in enumerate(original):
        key=line.partition('=')[0]
        if key in updates:
            if key in seen:
                raise ValueError('Duplicate origin key '+key)
            seen.add(key)
            original[idx]=key+'='+updates[key]+'\n'
    if seen!=set(updates):
        raise ValueError('Frozen installation lacks required origin keys')
    return {'.env':''.join(original).encode(), 'dashboard.json':(json.dumps(config,indent=2)+'\n').encode()}


def prepare(i, config, updates):
    files=desired(i, config, updates)
    state=i/'.private-origins'
    state.mkdir(mode=0o700)
    # Publish the recovery manifest before replacing either file.
    manifest={}
    for name,data in files.items():
        before=(i/name).read_bytes()
        atomic_write(state/name,before,0o600)
        manifest[name]=hashlib.sha256(data).hexdigest()
    atomic_write(state/'manifest.json',json.dumps(manifest).encode(),0o600)
    for name,data in files.items():
        atomic_write(i/name,data,0o600 if name=='.env' else 0o644)


def rollback(i):
    state=i/'.private-origins'
    manifest=json.loads((state/'manifest.json').read_text())
    names=('.env','dashboard.json')
    for name in names:
        current=(i/name).read_bytes()
        if current!=(state/name).read_bytes() and hashlib.sha256(current).hexdigest()!=manifest[name]:
            raise ValueError('Configuration changed since preparation. Review privately before rollback.')
    for name in names:
        atomic_write(i/name,(state/name).read_bytes(),0o600 if name=='.env' else 0o644)
    for name in (*names,'manifest.json'):
        (state/name).unlink()
    state.rmdir()
