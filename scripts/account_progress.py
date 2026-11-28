"""Persist only nonsecret account verification categories for the read-only launcher."""
import json,os,tempfile
from pathlib import Path
ALLOWED=set('music navidrome movies photos files passwords tasks monitor'.split())
def read(instance):
    p=Path(instance)/'data/.dashboard-metrics/accounts.json'
    try:
        if p.is_symlink() or p.stat().st_size>4096:return {}
        data=json.loads(p.read_text())
        return {k:v for k,v in data.items() if k in ALLOWED and v in ('verified','invited')}
    except (OSError,ValueError,AttributeError):return {}
def record(instance,app,state='verified'):
    if app not in ALLOWED or state not in ('verified','invited'):raise ValueError('Invalid account status')
    root=Path(instance)/'data/.dashboard-metrics'
    if not root.is_dir() or root.is_symlink():raise ValueError('Metrics directory unavailable')
    values=read(instance);values[app]=state
    if app=='music':values['navidrome']=state
    with tempfile.NamedTemporaryFile(dir=root,mode='w',delete=False) as out:
        tmp=Path(out.name)
        try:
            json.dump(values,out);out.flush();os.fchmod(out.fileno(),0o644);os.replace(tmp,root/'accounts.json')
        finally:tmp.unlink(missing_ok=True)
