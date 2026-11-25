#!/usr/bin/env python3
"""Read-only capacity and Intel render-device qualification; optional disposable encode."""
import argparse,json,os,re,stat,subprocess,sys,tempfile,fcntl
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def out(*cmd,timeout=30):return subprocess.check_output(cmd,text=True,stderr=subprocess.DEVNULL,timeout=timeout)
def capacity(ram,cores,profiles):
    # Conservative planning estimates, not measured simultaneous client capacity.
    estimates={'music':1.5,'movies':2,'photos':6,'files':2,'passwords':0.5,'tasks':1,'monitor':0.5,'dns':0.5}
    required=2+sum(estimates[p] for p in profiles)
    suggested=next((n for n in (8,16,32,64,128) if n>=required*1.25),None)
    return {'estimated_working_gib':required,'suggested_ram_gib':suggested,'ram_review':ram<required*1.25,'cpu_review':cores<(4 if 'photos' in profiles or 'movies' in profiles else 2),'recommendation':'Limit concurrent indexing and transcoding during acceptance; do not impose untested database memory limits.'}
def intel_render(sysroot=Path('/sys/class/drm'),devroot=Path('/dev/dri')):
    result=[]
    for p in sorted(sysroot.glob('renderD*')):
        try:
            if not re.fullmatch(r'renderD\d+',p.name) or (p/'device/vendor').read_text().strip()!='0x8086':continue
            driver=(p/'device/driver').resolve(strict=True).name
            device=devroot/p.name
            if driver not in ('i915','xe') or not stat.S_ISCHR(device.stat().st_mode):continue
            result.append({'device':str(device),'driver':driver,'group_id':device.stat().st_gid,'operator_access':os.access(device,os.R_OK|os.W_OK)})
        except OSError:continue
    return result
def inspect(i):
    e=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if e.get('INSTANCE_DIR')!=str(i) or not re.fullmatch('jobbi-[a-z0-9-]+',e.get('COMPOSE_PROJECT_NAME','')):raise ValueError('Invalid instance')
    profiles=set(filter(None,e['COMPOSE_PROFILES'].split(',')))
    ram=os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')/2**30
    cores=len(os.sched_getaffinity(0))
    ids=out('docker','ps','-q','--filter','label=com.docker.compose.project='+e['COMPOSE_PROJECT_NAME']).split()
    stats=[]
    if ids:
        for line in out('docker','stats','--no-stream','--format','{{json .}}',*ids,timeout=60).splitlines():
            d=json.loads(line);stats.append({k:d.get(k) for k in ('Name','CPUPerc','MemUsage','MemPerc','BlockIO','PIDs')})
    return {'ram_gib':round(ram,1),'logical_cpus':cores,'planning':capacity(ram,cores,profiles),'intel_render':intel_render(),'container_stats':stats,'hardware_transcoding':'not_qualified'}
def probe(i,device):
    # Use exact existing customer image, not a mutable pull. No customer mounts,
    # network, shell, privileges or persistent state. Only a generated test frame.
    devices={x['device']:x for x in intel_render()}
    if device not in devices:raise ValueError('Select detected Intel render node')
    cid=out('bash',str(ROOT/'scripts/ctl.sh'),str(i),'ps','-q','backend').strip()
    if not re.fullmatch('[0-9a-f]{12,64}',cid):raise ValueError('Running StreamHub backend required')
    image=out('docker','inspect','--format','{{.Image}}',cid).strip()
    if not re.fullmatch('sha256:[a-f0-9]{64}',image):raise ValueError('Invalid image ID')
    results={}
    for mode,args in [('software',['-c:v','libx264']),('intel_qsv',['-init_hw_device','vaapi=va:'+device,'-init_hw_device','qsv=qs@va','-filter_hw_device','qs','-vf','format=nv12,hwupload=extra_hw_frames=64','-c:v','h264_qsv'])]:
        # Hardware initialization must precede the input.
        prefix=args[:6] if mode=='intel_qsv' else []
        suffix=args[6:] if mode=='intel_qsv' else args
        command=['docker','run','--rm','--pull','never','--network','none','--read-only','--tmpfs','/tmp','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','512m','--cpus','2','--pids-limit','128','--user','65534:65534']
        if mode=='intel_qsv':command+=['--device',device+':'+device+':rw','--group-add',str(devices[device]['group_id'])]
        command+=['--entrypoint','ffmpeg',image,'-hide_banner','-loglevel','error',*prefix,'-f','lavfi','-i','testsrc2=size=320x240:rate=24','-t','1',*suffix,'-f','null','-']
        try:r=subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45);results[mode]='passed' if r.returncode==0 else 'unavailable'
        except subprocess.TimeoutExpired:results[mode]='timeout'
    return {'generated_sample':results,'hardware_transcoding':'probe_only; application playback and throughput not qualified'}
def cpu_plan(i,profile):
    if profile not in ('balanced','foreground'):raise ValueError('Unknown performance profile')
    env=i/'.env'
    st=env.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077 or os.geteuid()==0:raise ValueError('Original non-root operator and private environment required')
    text=env.read_text()
    values=dict(x.split('=',1) for x in text.splitlines() if '=' in x)
    if values.get('INSTANCE_DIR')!=str(i) or values.get('OWNER_UID')!=str(os.getuid()):raise ValueError('Instance mismatch')
    if any((i/n).exists() for n in ('.backup-running-services','.upgrade-hold.json')):raise ValueError('Reconcile backup or upgrade hold first')
    deployment=i/'deployment/compose.yaml'
    if deployment.read_text().count('cpu_shares: ${JOBBI_BACKGROUND_CPU_SHARES:-1024}')!=2:raise ValueError('Frozen deployment lacks the reviewed resource policy')
    profiles=set(values['COMPOSE_PROFILES'].split(','))
    services=[s for p,s in [('music','jobbi-storage-agent'),('photos','immich-machine-learning')] if p in profiles]
    if not services:raise ValueError('No supported background workers selected')
    shares=256 if profile=='foreground' else 1024
    lines=[x for x in text.splitlines() if not x.startswith('JOBBI_BACKGROUND_CPU_SHARES=')]
    return services,shares,'\n'.join(lines+[f'JOBBI_BACKGROUND_CPU_SHARES={shares}'])+'\n'
def set_cpu_policy(i,profile,apply):
    services,shares,body=cpu_plan(i,profile)
    command=['bash',str(ROOT/'scripts/ctl.sh'),str(i),'up','-d','--no-deps','--no-build','--pull','never','--force-recreate',*services]
    print(json.dumps({'background_cpu_shares':shares,'services':services,'recreate_required':True,'hard_cpu_cap':False,'apply_command':command},indent=2))
    if not apply:return
    # Stage configuration only; never restart workers silently. Coordinate
    # recreation with indexing jobs, backup windows and customer approval.
    with (i/'.backup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        _,_,body=cpu_plan(i,profile)
        with tempfile.NamedTemporaryFile(dir=i,mode='w',delete=False) as tmp:
            try:
                tmp.write(body);tmp.flush();os.fchmod(tmp.fileno(),0o600);os.fsync(tmp.fileno());os.replace(tmp.name,i/'.env')
            finally:Path(tmp.name).unlink(missing_ok=True)
    print('Policy saved; recreate only the listed workers during a reviewed maintenance window. Use balanced to revert.')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--probe-device');p.add_argument('--apply-probe',action='store_true');p.add_argument('--cpu-profile',choices=['balanced','foreground']);p.add_argument('--apply-policy',action='store_true');a=p.parse_args();i=a.instance.resolve()
    if a.cpu_profile:
        if a.apply_probe:p.error('Choose one operation')
        set_cpu_policy(i,a.cpu_profile,a.apply_policy);return
    if a.apply_policy:p.error('Select CPU profile')
    result=inspect(i)
    if a.apply_probe:
        if not a.probe_device:p.error('Specify detected Intel render node')
        result['encode_probe']=probe(i,a.probe_device)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Performance review unavailable: '+type(e).__name__)
