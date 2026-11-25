"""Fresh offline install bundle: immutable images and exact committed sources, no instance data."""
import json,os,re,subprocess
from pathlib import Path
from offline_kit import verify,digest,HELPER
from recovery_images import image_plan
def check(bundle,release,apps):
    b=Path(bundle)
    if b.is_symlink() or not b.is_dir() or set(x.name for x in b.iterdir())!={'kit','images.tar.gz','inventory.json','bundle.json'}:raise ValueError('Invalid install bundle layout')
    for name in ('images.tar.gz','inventory.json','bundle.json'):
        p=b/name
        if p.is_symlink() or not p.is_file():raise ValueError('Invalid bundle file')
    m=json.loads((b/'bundle.json').read_text())
    if m.get('schema')!=1 or m.get('release')!=release or set(m.get('apps',[]))!=set(apps):raise ValueError('Bundle release or application selection mismatch')
    for name in ('images.tar.gz','inventory.json'):
        if digest(b/name)!=m['files'][name]:raise ValueError('Bundle checksum mismatch')
    k=verify(b/'kit',release)
    inventory=json.loads((b/'inventory.json').read_text());image_plan(inventory)
    return inventory,k
