"""Fresh paired pilot tailnet approval, independent of functional acceptance."""
import fcntl,json,os,re,subprocess,sys
from pathlib import Path
from account_progress import read as accounts
from private_origins import atomic_write
ROOT=Path(__file__).resolve().parents[1]
APPROVAL='.pilot-tailnet-approval.json'
def hostname(raw):
    if not isinstance(raw,str) or len(raw)>254:raise ValueError('Invalid tailnet name')
    h=raw.rstrip('.').lower()
    if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){2,}net',h) or not h.endswith('.ts.net'):raise ValueError('Require customer MagicDNS name')
    return h
def eligibility(i,e,c,options):
    if i.name!='laptop-test' or e.get('INSTANCE_DIR')!=str(i) or e.get('BIND_IP')!='127.0.0.1' or e.get('COMPOSE_PROJECT_NAME')!='jobbi-laptop-test' or e.get('OWNER_UID')!=str(os.getuid()) or os.geteuid()==0:raise ValueError('Dedicated fresh pilot operator required')
    selected={x['id'] for x in c['apps']}
    if not selected or selected-{'music','navidrome','movies','photos','files','passwords','tasks','monitor','dns'}:raise ValueError('Unsupported application origin')
    if any((i/x).exists() or (i/x).is_symlink() for x in ('.pilot-lan-client.json','.pilot-dns-native-pending','.upgrade-hold.json','.backup-running-services','deployment/pilot-network.json')):raise ValueError('Existing LAN or maintenance configuration needs review')
    if 'invidious' in options or (i/'data/pilot-media/invidious-source').exists():raise ValueError('Invidious origin migration requires review')
    if any(v!='ready' for v in options.values()):raise ValueError('Resolve optional service state first')
    statuses=accounts(i)
    for app in selected-{'dns'}:
        if statuses.get(app)!=('invited' if app=='passwords' else 'verified'):raise ValueError('Core account verification incomplete')
    if 'dns' in selected and ('dns' not in e.get('COMPOSE_PROFILES','').split(',') or options.get('dns')!='ready'):raise ValueError('Verify native DNS before exposing its admin interface')
def check_approval(i,e,c,host,options):
    p=i/APPROVAL
    if p.is_symlink() or not p.is_file() or p.stat().st_size>4096 or p.stat().st_mode&0o077:raise ValueError('Private paired approval required')
    if json.loads(p.read_text())!={'schema':1,'instance':str(i),'host':hostname(host),'consent':True}:raise ValueError('Tailnet approval differs')
    eligibility(i,e,c,options)
def finish(i,data,status,options):
    if not isinstance(data,dict) or set(data)!={'consent','host'} or data['consent'] is not True or status.get('state')!='Running':raise ValueError('Explicit approval and running customer tailnet required')
    host=hostname(data['host'])
    if host!=hostname(status.get('host')):raise ValueError('Tailnet name changed; review again')
    with (i/'.backup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        e=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
        c=json.loads((i/'dashboard.json').read_text())
        eligibility(i,e,c,options)
        pending=(APPROVAL,'.private-serve.json','.private-origins','.nextcloud-origin.json')
        if any((i/x).exists() or (i/x).is_symlink() for x in pending) or any(a.get('url') for a in c['apps']):raise ValueError('Previous access transaction must be reviewed')
        atomic_write(i/APPROVAL,json.dumps({'schema':1,'instance':str(i),'host':host,'consent':True}).encode(),0o600)
        cmd=[sys.executable,str(ROOT/'scripts/finish-private-access.py'),str(i),'--paired-setup','--apply']
        try:
            subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except (OSError,subprocess.SubprocessError):
            # Only permit retry after the existing transaction fully rolled back.
            if not any((i/x).exists() for x in pending[1:]):(i/APPROVAL).unlink(missing_ok=True)
            raise ValueError('Private access failed; review retained transaction if present')
        return 'https://'+host+':19443/'
