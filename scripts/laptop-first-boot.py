#!/usr/bin/env python3
"""Single-SSD pilot first boot. Explicit installer disk selection; never formats an existing LV."""
import ipaddress,json,os,pwd,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=Path('/srv/jobbi-data')
LV=Path('/dev/ubuntu-vg/jobbi-data')
STATE=Path('/var/lib/jobbi')
APPS='music,movies,photos,files,passwords,tasks,monitor'
def out(*cmd):return subprocess.check_output(cmd,text=True).strip()
def run(*cmd,**kw):subprocess.run(cmd,check=True,**kw)
def data_volume():
    root=out('findmnt','-n','-o','SOURCE','--target','/')
    if Path(root).resolve()!=Path('/dev/ubuntu-vg/ubuntu-lv').resolve():raise ValueError('Select guided Ubuntu LVM on the approved SSD')
    rows=json.loads(out('vgs','--reportformat','json','--units','b','--nosuffix','-o','vg_name,pv_count,vg_free','ubuntu-vg'))['report'][0]['vg']
    if len(rows)!=1 or int(rows[0]['pv_count'])!=1:raise ValueError('Require one physical volume in OS VG')
    lvs=json.loads(out('lvs','--reportformat','json','-o','lv_name','ubuntu-vg'))['report'][0]['lv']
    if {x['lv_name'] for x in lvs}-{'ubuntu-lv','jobbi-data'}:raise ValueError('Unexpected existing logical volumes; inspect')
    if not LV.exists():
        free=int(float(rows[0]['vg_free']))//(1024**3);size=min(300,free-8)
        if size<60:raise ValueError('Leave at least 68 GiB free in guided LVM')
        run('lvcreate','-L',str(size)+'G','-n','jobbi-data','ubuntu-vg')
        run('mkfs.ext4','-L','jobbi-data',str(LV))
    if out('blkid','-s','TYPE','-o','value',str(LV))!='ext4':raise ValueError('Existing data LV not ext4; no automatic reformat')
    uuid=out('blkid','-s','UUID','-o','value',str(LV))
    if not re.fullmatch('[a-fA-F0-9-]+',uuid):raise ValueError('Invalid data UUID')
    DATA.mkdir(exist_ok=True)
    if not DATA.is_mount():
        if any(DATA.iterdir()):raise ValueError('Unmounted data directory nonempty')
        run('mount',str(LV),str(DATA))
    run('findmnt','--noheadings','--mountpoint',str(DATA),'--source','UUID='+uuid)
    f=Path('/etc/fstab');matches=[x.split() for x in f.read_text().splitlines() if x.strip() and not x.lstrip().startswith('#') and len(x.split())>1 and x.split()[1]==str(DATA)]
    if matches and (len(matches)!=1 or matches[0][0]!='UUID='+uuid):raise ValueError('Existing fstab entry differs')
    if not matches:
        with f.open('a') as stream:stream.write('UUID='+uuid+' '+str(DATA)+' ext4 defaults 0 2\n')
    run('systemctl','daemon-reload');run('findmnt','--verify')
    return root
def private_ip():
    rows=json.loads(out('ip','-j','-4','route','show','default'))
    if len(rows)!=1 or not rows[0].get('dev'):raise ValueError('Require one default interface on isolated private lab network')
    dev=rows[0]['dev'];rows=json.loads(out('ip','-j','-4','addr','show','dev',dev))
    ips=[x['local'] for row in rows for x in row.get('addr_info',[]) if x.get('scope')=='global']
    if len(ips)!=1 or not any(ipaddress.IPv4Address(ips[0]) in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):raise ValueError('Require single RFC1918 IPv4 on selected interface')
    return ips[0],str(ipaddress.IPv4Interface(ips[0]+'/'+str(next(x['prefixlen'] for row in rows for x in row.get('addr_info',[]) if x.get('local')==ips[0]))).network)
def setup_service(instance,user):
    addr,network=private_ip();directory=Path('/etc/jobbi/pilot-tls')
    directory.mkdir(parents=True,exist_ok=True,mode=0o750)
    os.chown(directory,0,user.pw_gid)
    cert=directory/'cert.pem';key=directory/'key.pem'
    if cert.exists() or key.exists():raise ValueError('Existing pilot TLS identity; inspect rather than overwrite')
    run('openssl','req','-x509','-newkey','rsa:3072','-sha256','-nodes','-days','7','-subj','/CN=JobbiSoft Home Pilot','-addext','subjectAltName=IP:'+addr,'-keyout',str(key),'-out',str(cert),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.chown(key,0,user.pw_gid);key.chmod(0o640);cert.chmod(0o644)
    fp=out('openssl','x509','-in',str(cert),'-noout','-fingerprint','-sha256').split('=',1)[1]
    cfg=directory/'setup.json';cfg.write_text(json.dumps({'address':addr,'network':network,'operator':user.pw_name,'instance':str(instance),'cert':str(cert),'key':str(key),'fingerprint':fp}));cfg.chmod(0o644)
    unit=Path('/etc/systemd/system/jobbi-pilot-setup.service')
    if unit.exists():raise ValueError('Existing setup unit; review')
    unit.write_text('[Unit]\nDescription=Jobbi isolated LAN pairing (pilot)\nAfter=network-online.target docker.service\nWants=network-online.target\nRequires=docker.service\nConflicts=getty@tty3.service\n[Service]\nType=simple\nUser='+user.pw_name+'\nUMask=0077\nRestart=no\nRestartForceExitStatus=75\nRestartSec=3s\nExecStart=/usr/bin/python3 '+str(ROOT/'scripts/setup-web.py')+' '+str(instance)+' --port 18080 --minutes 60 --pilot-lan '+str(cfg)+'\nExecStopPost=+/usr/bin/python3 '+str(ROOT/'scripts/pilot-lan-gateway.py')+'\nStandardOutput=tty\nStandardError=tty\nTTYPath=/dev/tty3\n[Install]\nWantedBy=multi-user.target\n')
    run('systemctl','daemon-reload')
    # Pairing token expires and is rotated on the physical console only while
    # this initial setup service is running; successful pairing does not restart.
    run('systemctl','start','jobbi-pilot-setup.service')
    if shutil.which('chvt'):run('chvt','3')
def main():
    if os.geteuid()!=0 or out('git','-C',str(ROOT),'rev-parse','HEAD')!=Path('/etc/jobbi/pilot-revision').read_text().strip():raise ValueError('Pinned root checkout required')
    user=pwd.getpwuid(1000)
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',user.pw_name):raise ValueError('Invalid first Ubuntu operator')
    if out('docker','ps','-aq'):raise ValueError('Existing Docker containers: refuse automatic provisioning')
    if (DATA/'laptop-test').exists():raise ValueError('Existing instance: refuse overwrite')
    root=data_volume();os.chown(DATA,user.pw_uid,user.pw_gid)
    run('usermod','-aG','docker',user.pw_name)
    run(sys.executable,str(ROOT/'scripts/boot-guard.py'),str(DATA),'--apply')
    env={**os.environ,'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'safe.directory','GIT_CONFIG_VALUE_0':str(ROOT),'HOME':user.pw_dir}
    prefix=['runuser','-u',user.pw_name,'--']
    run(*prefix,sys.executable,str(ROOT/'scripts/preflight.py'),'--data-root',str(DATA),'--apps',APPS,env=env)
    run(*prefix,sys.executable,str(ROOT/'scripts/install.py'),'--name','laptop-test','--data-root',str(DATA),'--apps',APPS,'--bind','127.0.0.1','--music-admin',user.pw_name,'--tz','America/Ciudad_Juarez',env=env)
    instance=DATA/'laptop-test'
    for attempt in range(30):
        if subprocess.run([*prefix,'bash',str(ROOT/'scripts/verify.sh'),str(instance)],env=env).returncode==0:break
        time.sleep(10)
    else:raise ValueError('Services not ready; preserve instance for review')
    # Link the instance's own provider before pairing. The movie account step
    # retries if the provider was temporarily unavailable during first boot.
    try:
        run(*prefix,sys.executable,str(ROOT/'scripts/connect-movies.py'),str(instance),env=env,timeout=360)
    except (OSError,subprocess.SubprocessError):
        print('Prowlarr connection pending; retry during movie account setup',flush=True)
    devices=[]
    # Select only physical disk ancestry of the approved OS LV.
    rows=json.loads(out('lsblk','-J','-s','-p','-o','NAME,TYPE',root))['blockdevices']
    def walk(xs):
        for x in xs:
            if x['type']=='disk':devices.append(Path(x['name']).resolve())
            walk(x.get('children',[]))
    walk(rows);aliases=[]
    for d in set(devices):
        match=sorted(x for x in Path('/dev/disk/by-id').glob('*') if re.fullmatch('[A-Za-z0-9_.:+-]+',x.name) and x.resolve()==d)
        if match:aliases.extend(['--smart-device',str(match[0])])
    run(sys.executable,str(ROOT/'scripts/install-health-service.py'),str(instance),'--no-backup','--operator',user.pw_name,'--check-updates',*aliases,'--apply')
    # Install the private networking client without enrolling or accepting DNS/routes.
    try:
        run('bash',str(ROOT/'scripts/customer-remote.sh'))
        # The first appliance operator already has Docker administration rights.
        # Delegate only on this new dedicated host, without enrolling any account.
        run('tailscale','set','--operator='+user.pw_name)
    except (OSError,subprocess.SubprocessError):print('Optional Tailscale package unavailable; local setup continues',flush=True)
    setup_service(instance,user)
    STATE.mkdir(mode=0o700,exist_ok=True);(STATE/'pilot-provisioned').write_text('Installed; browser onboarding and private access pending\n')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:sys.exit('Jobbi first boot stopped: '+str(exc))
