#!/usr/bin/env python3
"""Read-only local diagnostics. No credentials, SMART changes, or uploaded logs."""
import argparse,json,shutil,subprocess,os,datetime
from pathlib import Path
def run(*args):
    try:
        r=subprocess.run(args,capture_output=True,text=True,timeout=20)
        return r.stdout.strip() if r.returncode==0 else None
    except (OSError,subprocess.TimeoutExpired):return None
def inspect(instance):
    instance=Path(instance).resolve()
    env=dict(x.split('=',1) for x in (instance/'.env').read_text().splitlines() if '=' in x)
    if env.get('INSTANCE_DIR')!=str(instance) or not env.get('COMPOSE_PROJECT_NAME','').startswith('jobbi-'):raise ValueError('Invalid AIO instance')
    alerts=[];fs=shutil.disk_usage(instance);free=round(fs.free/fs.total*100,1)
    if free<15:alerts.append('Data filesystem under 15% free')
    mem={}
    try:
        lines=dict((x.split(':',1)[0],int(x.split()[1])) for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemTotal:','MemAvailable:')))
        mem={k:round(v/1024**2,2) for k,v in lines.items()}
        if lines['MemAvailable']<lines['MemTotal']*.1:alerts.append('RAM under 10% available')
    except (OSError,ValueError,KeyError):alerts.append('RAM unavailable')
    temperatures=[]
    for p in Path('/sys/class/thermal').glob('thermal_zone*'):
        try:
            value=round(int((p/'temp').read_text())/1000,1)
            if -20<=value<=150:
                temperatures.append({'sensor':(p/'type').read_text().strip(),'celsius':value})
                if value>=85:alerts.append('High thermal-zone reading; check sensor-specific limits')
        except (OSError,ValueError):pass
    services=run('bash',str(Path(__file__).resolve().parent/'ctl.sh'),str(instance),'ps','-a','--format','json')
    parsed=[]
    if services is not None:
        try:
            for line in services.splitlines():
                obj=json.loads(line)
                for x in obj if isinstance(obj,list) else [obj]:
                    item={k:x.get(k) for k in ('Service','State','Health')}
                    parsed.append(item)
                    if item['State']!='running' or item['Health']=='unhealthy':alerts.append('Service needs review: '+str(item['Service']))
        except (ValueError,TypeError):alerts.append('Compose status unreadable')
    else:alerts.append('Compose status unavailable')
    # lsblk lists devices but does not claim SMART health; privileged testing remains explicit.
    disks=run('lsblk','-J','-d','-o','NAME,SIZE,MODEL,ROTA,TYPE')
    try:devices=json.loads(disks)['blockdevices'] if disks else []
    except (ValueError,KeyError):devices=[]
    dockerroot=run('docker','info','--format','{{.DockerRootDir}}')
    dockerfree=None
    if dockerroot and Path(dockerroot).is_dir():
        df=shutil.disk_usage(dockerroot);dockerfree=round(df.free/df.total*100,1)
        if dockerfree<15:alerts.append('Docker filesystem under 15% free')
    return {'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'project':env['COMPOSE_PROJECT_NAME'],'data_free_percent':free,'docker_free_percent':dockerfree,'ram_gib':mem,'load_average':os.getloadavg(),'thermal_zones':temperatures,'disks':devices,'smart':'Not tested; use authorized smartctl read-only checks on exact disks','services':parsed,'alerts':alerts}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance');a=p.parse_args();d=inspect(a.instance);print(json.dumps(d,indent=2));return bool(d['alerts'])
if __name__=='__main__':raise SystemExit(main())
