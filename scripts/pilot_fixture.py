"""Paths and private fixture storage for the disposable office recovery CI job."""
import json
import os
from pathlib import Path

def location():
    instance=Path(os.environ.get('JOBBI_PILOT_INSTANCE','/tmp/jobbi-full/full'))
    if os.environ.get('GITHUB_ACTIONS')!='true' or str(instance) not in (
        '/tmp/jobbi-full/full','/tmp/jobbi-office/source','/tmp/jobbi-office/recovered'):
        raise ValueError('Disposable CI only')
    return instance

def save(name, values):
    path=Path('/tmp/jobbi-office')/(name+'.json')
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as out:
        json.dump(values,out)

def load(name):
    return json.loads((Path('/tmp/jobbi-office')/(name+'.json')).read_text())
