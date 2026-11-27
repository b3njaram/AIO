"""Explicit, bounded optional-service operations for the authenticated physical setup."""
import json,os,re,socket,struct,subprocess,sys,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from private_origins import atomic_write
from pilot_media import SOULSEEK_LOGIN_PROBE
ROOT=Path(__file__).resolve().parents[1]
IDS=('soulseek','invidious','dns')
def validate(data):
    if not isinstance(data,dict) or set(data)!={'services','consent','dns_password'}:raise ValueError('Invalid optional setup request')
    selected=data['services'];pw=data['dns_password']
    if not isinstance(selected,list) or not selected or not all(isinstance(x,str) and x in IDS for x in selected) or len(set(selected))!=len(selected) or data['consent'] is not True:raise ValueError('Explicit service consent required')
    if not isinstance(pw,str) or ('dns' in selected and (not 12<=len(pw)<=128 or any(c in pw for c in '\n\r\x00$'))) or ('dns' not in selected and pw):raise ValueError('Invalid independent DNS admin password')
    return selected,pw
def read(i):
    try:
        p=i/'.pilot-options.json'
        if p.is_symlink() or p.stat().st_size>4096:return {}
        d=json.loads(p.read_text())
        return {k:v for k,v in d.items() if k in IDS and v in ('ready','review','starting')}
    except (OSError,ValueError,AttributeError):return {}
def http_ready(port,path):
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:'+str(port)+path,timeout=5) as response:return 200<=response.status<400
    except OSError:return False
def dns_ready():
    # Query a known local Pi-hole record over the isolated listener; no household DNS changes.
    query=struct.pack('!6H',0x4a42,0x0100,1,0,0,0)+b'\x02pi\x04hole\x00'+struct.pack('!2H',1,1)
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.settimeout(4);s.connect(('127.0.0.1',1053));s.send(query);answer=s.recv(4096)
        if len(answer)<12:return False
        ident,flags,qd,an,_,_=struct.unpack('!6H',answer[:12])
        return ident==0x4a42 and bool(flags&0x8000) and not(flags&15) and an>0
    except OSError:return False
def provision(i,address,selected,pw):
    result=read(i)
    if any(k in result for k in selected):raise ValueError('Existing provider state retained; do not create duplicate accounts')
    def save():
        atomic_write(i/'.pilot-options.json',json.dumps(result).encode(),0o600)
    def run(cmd,stdin=None):
        try:
            return subprocess.run(cmd,input=stdin,text=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=900,check=False).returncode==0
        except (OSError,subprocess.TimeoutExpired):return False
    for k in selected:result[k]='starting'
    save()
    media=[k for k in selected if k in ('soulseek','invidious')]
    if media:
        cmd=[sys.executable,str(ROOT/'scripts/pilot-media.py'),str(i),'--apply']
        if 'soulseek' in media:cmd+=['--soulseek']
        if 'invidious' in media:cmd+=['--invidious','--invidious-public-url','https://'+address+':18091']
        # Do not echo subprocess output or credentials into the browser or logs.
        ok=run(cmd)
        if 'soulseek' in media:
            probe=['bash',str(ROOT/'scripts/ctl.sh'),str(i),'exec','-T','jobbi-music','node','--input-type=module','-e',SOULSEEK_LOGIN_PROBE]
            result['soulseek']='ready' if ok and run(probe) else 'review'
        if 'invidious' in media:
            result['invidious']='ready' if ok and http_ready(18091,'/') else 'review'
        save()
    if 'dns' in selected:
        ok=run([sys.executable,str(ROOT/'scripts/pilot-dns.py'),str(i),'--apply','--password-stdin'],pw+'\n')
        result['dns']='ready' if ok and http_ready(18089,'/admin/') and dns_ready() else 'review'
        save()
    return result
def tailnet_status():
    # Only return a bounded, sanitized state and the official short-lived login URL.
    try:
        raw=subprocess.run(['tailscale','status','--json'],capture_output=True,text=True,timeout=10)
        d=json.loads(raw.stdout);state=d.get('BackendState','Unknown')
    except (OSError,ValueError,subprocess.TimeoutExpired):return {'state':'Unavailable'}
    if state not in ('Running','NeedsLogin','NoState','Stopped','Starting','NeedsMachineAuth'):state='Unknown'
    result={'state':state}
    url=d.get('AuthURL','')
    if isinstance(url,str) and len(url)<=512 and re.fullmatch(r'https://login\.tailscale\.com/a/[A-Za-z0-9_-]+',url):result['url']=url
    return result
def tailnet_connect():
    status=tailnet_status()
    if status['state']=='Running':return status
    if status['state'] not in ('NeedsLogin','NoState','Stopped','Starting'):raise ValueError('Tailscale unavailable or awaiting administrator approval')
    # Never switch an existing account, accept routes/DNS or use an auth key.
    if 'url' not in status:
        try:subprocess.run(['tailscale','up','--json','--timeout=8s','--accept-dns=false','--accept-routes=false'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=12)
        except (OSError,subprocess.TimeoutExpired):pass
    return tailnet_status()
