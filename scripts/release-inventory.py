#!/usr/bin/env python3
"""Record actual customer container images, without inspecting environment or secrets."""
import argparse,datetime as dt,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def output(*args):return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL).strip()
def collect(instance):
    i=Path(instance).resolve()
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x and not x.startswith('#'))
    project=env.get('COMPOSE_PROJECT_NAME','')
    if not re.fullmatch('jobbi-[a-z0-9-]+',project) or env.get('INSTANCE_DIR')!=str(i):raise ValueError('Invalid customer instance')
    ids=output('docker','ps','-a','-q','--filter','label=com.docker.compose.project='+project).splitlines()
    if not ids:raise ValueError('No customer containers')
    services={}
    for cid in ids:
        # Format fields only: no container environment, credentials or mount paths.
        fields=output('docker','inspect','--format','{{index .Config.Labels "com.docker.compose.service"}}|{{.Image}}|{{.Config.Image}}',cid).split('|')
        if len(fields)!=3:raise ValueError('Invalid container metadata')
        service,image,reference=fields
        if not re.fullmatch('[a-zA-Z0-9_-]+',service) or not re.fullmatch('sha256:[0-9a-f]{64}',image):raise ValueError('Invalid image identity')
        if service in services and services[service]['id']!=image:raise ValueError('Multiple image versions for service '+service)
        digests=json.loads(output('docker','image','inspect','--format','{{json .RepoDigests}}',image)) or []
        services[service]={'id':image,'reference':reference,'repo_digests':digests}
    return {'schema':1,'recorded':dt.datetime.now(dt.timezone.utc).isoformat(),'project':project,'services':services}
def compare(expected,current):
    a=expected['services'];b=current['services']
    return [{'service':k,'expected':a.get(k,{}).get('id'),'current':b.get(k,{}).get('id')} for k in sorted(set(a)|set(b)) if a.get(k,{}).get('id')!=b.get(k,{}).get('id')]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--record',action='store_true');p.add_argument('--compare',type=Path);a=p.parse_args()
    state=collect(a.instance)
    if a.record:
        os.umask(0o077);i=a.instance.resolve();tmp=i/'image-inventory.tmp';tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(i/'image-inventory.json')
    if a.compare:
        differences=compare(json.loads(a.compare.read_text()),state)
        print(json.dumps({'differences':differences},indent=2));return bool(differences)
    print(json.dumps(state,indent=2));return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:sys.exit('Inventory unavailable: '+type(e).__name__)
