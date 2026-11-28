"""Validate and migrate only the existing opt-in local Invidious overlay."""
import json
from pathlib import Path
from urllib.parse import urlsplit
from pilot_media import public_origin

def overlay(i):
    p=i/'deployment/pilot-media.json'
    if p.is_symlink() or not p.is_file() or p.stat().st_size>65536 or p.stat().st_mode&0o077:
        raise ValueError('Require private complete media overlay')
    d=json.loads(p.read_text())
    services=d['services']
    if set(services)-{'slskd','jobbi-music','invidious','invidious-db','invidious-companion'}:
        raise ValueError('Unexpected media services')
    if not {'jobbi-music','invidious','invidious-db','invidious-companion'}<=set(services):
        raise ValueError('Incomplete Invidious overlay')
    iv=services['invidious']
    if iv.get('ports')!=['127.0.0.1:18091:3000'] or any(services[k].get('ports') for k in ('invidious-db','invidious-companion')):
        raise ValueError('Require isolated Invidious bindings')
    music=services['jobbi-music']['environment']
    if music.get('JOBBI_LOCAL_INVIDIOUS')!='true' or music.get('INVIDIOUS_URL')!='disabled' or music.get('INVIDIOUS_BACKUPS')!='':
        raise ValueError('Require instance-local fallback adapter')
    current=public_origin(music['JOBBI_INVIDIOUS_PUBLIC_ORIGIN'])
    cfg=json.loads(iv['environment']['INVIDIOUS_CONFIG'])
    u=urlsplit(current)
    if (cfg.get('domain'),cfg.get('external_port'),cfg.get('https_only'))!=(u.hostname,u.port,True):
        raise ValueError('Invidious canonical origin differs from music')
    if not (i/'data/pilot-media/invidious-adapter.before').is_file():
        raise ValueError('Missing original adapter evidence')
    return d

def desired(i,origin):
    d=overlay(i)
    origin=public_origin(origin)
    u=urlsplit(origin)
    if not u.hostname.endswith('.ts.net'):raise ValueError('Require private tailnet origin')
    services=d['services']
    cfg=json.loads(services['invidious']['environment']['INVIDIOUS_CONFIG'])
    cfg.update(domain=u.hostname,external_port=u.port,https_only=True)
    services['invidious']['environment']['INVIDIOUS_CONFIG']=json.dumps(cfg)
    services['jobbi-music']['environment']['JOBBI_INVIDIOUS_PUBLIC_ORIGIN']=origin
    return json.dumps(d).encode()
