#!/usr/bin/env python3
"""Read-only local diagnostics. No credentials, SMART changes, or uploaded logs."""
import argparse,json,shutil,subprocess,os,datetime
from pathlib import Path
def run(*args):
    try:
        r=subprocess.run(args,capture_output=True,text=True,timeout=20)
        return r.stdout.strip() if r.returncode==0 else None
    except (OSError,subprocess.TimeoutExpired):return None
def parse_smart(data,code):
    """Summarize without exposing serials or treating command errors as health."""
    if not isinstance(data,dict):return {'state':'unknown'}
    temp=data.get('temperature') or {}
    health=(data.get('smart_status') or {}).get('passed')
    nvme=data.get('nvme_smart_health_information_log') or {}
    errors=nvme.get('media_errors')
    warning=nvme.get('critical_warning')
    attrs=(data.get('ata_smart_attributes') or {}).get('table',[])
    counts={}
    for a in attrs:
        if a.get('id') in (5,187,197,198):
            counts[str(a['id'])]=(a.get('raw') or {}).get('value')
    # smartctl return bitmask: bits 0-2 command/device errors, bit 3 health failed,
    # bits 4-7 SMART thresholds or history. Do not equate history with imminent failure.
    if code&7:state='unknown'
    elif health is False or code&8 or isinstance(warning,int) and warning:state='failed'
    elif code&240 or any(isinstance(v,int) and v>0 for v in counts.values()) or isinstance(errors,int) and errors>0:state='review'
    elif health is True:state='passed'
    else:state='unknown'
    return {'state':state,'temperature_c':temp.get('current',nvme.get('temperature')),'ata_raw_counts':counts,'nvme_media_errors':errors,'nvme_critical_warning':warning}
def smart_device(device):
    import re,stat
    # Explicit block devices only. No implicit enumeration or sudo.
    p=Path(device)
    if not re.fullmatch(r'/dev/(?:sd[a-z]+|nvme\d+n\d+|hd[a-z]+)',str(p)) or not stat.S_ISBLK(p.stat().st_mode):raise ValueError('Specify an exact whole block device, e.g. /dev/sda')
    if not shutil.which('smartctl'):return {'device':str(p),'state':'unknown','reason':'smartctl unavailable'}
    try:
        r=subprocess.run(['smartctl','-j','-H','-A',str(p)],capture_output=True,text=True,timeout=30)
        return {'device':str(p),**parse_smart(json.loads(r.stdout),r.returncode)}
    except (OSError,ValueError,subprocess.TimeoutExpired):return {'device':str(p),'state':'unknown','reason':'SMART query unavailable'}
def inspect(instance,smart=()):
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
    smart_results=[smart_device(x) for x in smart]
    for x in smart_results:
        if x['state']!='passed':alerts.append('SMART '+x['state']+': '+x['device'])
    if not parsed:alerts.append('No service status available')
    return {'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'project':env['COMPOSE_PROJECT_NAME'],'data_free_percent':free,'docker_free_percent':dockerfree,'ram_gib':mem,'load_average':os.getloadavg(),'thermal_zones':temperatures,'disks':devices,'smart':smart_results or 'Not tested; specify --smart-device for authorized read-only checks','services':parsed,'alerts':alerts}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance');p.add_argument('--smart-device',action='append',default=[]);a=p.parse_args();d=inspect(a.instance,a.smart_device);print(json.dumps(d,indent=2));return bool(d['alerts'])
if __name__=='__main__':raise SystemExit(main())
