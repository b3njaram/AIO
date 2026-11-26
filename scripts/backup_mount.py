"""Identify a mounted backup filesystem without recording device paths in units."""
import hashlib
import json
from pathlib import Path
import subprocess


def mount_identity(path):
    data=subprocess.check_output(['findmnt','--json','--target',str(Path(path).resolve()),
                                  '--output','TARGET,SOURCE,FSTYPE,UUID'],text=True)
    rows=json.loads(data).get('filesystems',[])
    if len(rows)!=1:raise ValueError('Cannot identify backup mount')
    row=rows[0]
    fields=[row['target'],row['fstype'],row.get('uuid') or row['source']]
    if not all(fields):raise ValueError('Backup filesystem identity is incomplete')
    return hashlib.sha256(json.dumps(fields).encode()).hexdigest()
