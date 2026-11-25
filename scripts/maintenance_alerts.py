"""Sanitized local alerts and optional customer-owned private HTTPS delivery."""
import datetime as dt,json,math,os,re,stat,tempfile,urllib.request,urllib.parse
from pathlib import Path
CODES={'storage_low','system_disk_low','temperature_high','drive_failed','drive_review','raid_degraded','backup_overdue','backup_unverified','backup_missing','services_review','health_stale','update_available','recovery_review'}
def now():return dt.datetime.now(dt.timezone.utc)
def alerts(s):
    found=set()
    def numeric(v):return type(v) in (int,float) and math.isfinite(v)
    try:
        at=dt.datetime.fromisoformat(s['at'])
        if not now()-dt.timedelta(minutes=45)<=at<=now()+dt.timedelta(minutes=1):raise ValueError()
    except (TypeError,ValueError,KeyError):return ['health_stale']
    for k,c in [('data_free_percent','storage_low'),('docker_free_percent','system_disk_low')]:
        if numeric(s.get(k)) and s[k]<15:found.add(c)
    if any(numeric(x) and x>=85 for x in s.get('temperature_c',[])):found.add('temperature_high')
    for d in s.get('drives',[]):
        if d.get('state')=='failed':found.add('drive_failed')
        elif d.get('state')!='passed':found.add('drive_review')
        if numeric(d.get('temperature_c')) and d['temperature_c']>=60:found.add('temperature_high')
    if s.get('storage',{}).get('redundancy',{}).get('state')=='degraded':found.add('raid_degraded')
    backup=s.get('backup',{}).get('state')
    if backup=='stale':found.add('backup_overdue')
    elif backup=='mount_unavailable':found.add('backup_missing')
    elif backup!='verified':found.add('backup_unverified')
    if not numeric(s.get('service_alert_count')) or s['service_alert_count']>0:found.add('services_review')
    if s.get('updates',{}).get('state')=='review_available':found.add('update_available')
    if s.get('recovery',{}).get('state')=='review_required':found.add('recovery_review')
    return sorted(found)
def private_url(value):
    u=urllib.parse.urlsplit(value)
    if u.scheme!='https' or not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+\.ts\.net',u.hostname or '') or u.username or u.password or u.query or u.fragment or u.netloc not in (u.hostname,u.hostname+':443') or not re.fullmatch(r'/[A-Za-z0-9_-]{8,100}',u.path):raise ValueError('Use an exact customer-owned HTTPS .ts.net notification topic on port 443')
    return value
def private_read(p,uid):
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'r') as f:
        st=os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=uid or st.st_mode&0o077 or st.st_size>16384:raise ValueError('Unsafe notification configuration')
        return json.load(f)
def atomic(p,obj):
    with tempfile.NamedTemporaryFile(dir=p.parent,mode='w',delete=False) as out:
        tmp=Path(out.name)
        try:
            json.dump(obj,out);out.flush();os.fsync(out.fileno());os.fchmod(out.fileno(),0o600);os.replace(tmp,p)
        finally:tmp.unlink(missing_ok=True)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Notification redirect refused')
def deliver(url,token,codes):
    private_url(url)
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_.~-]{16,512}',token):raise ValueError('Private notification token required')
    # Only fixed categories, never paths, disk IDs, usernames, addresses or logs.
    if any(c not in CODES for c in codes):raise ValueError('Invalid alert category')
    payload=('JobbiSoft Home maintenance: '+(', '.join(codes) if codes else 'previous alerts cleared')).encode()
    request=urllib.request.Request(url,data=payload,headers={'Authorization':'Bearer '+token,'Content-Type':'text/plain; charset=utf-8','Title':'JobbiSoft Home'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(request,timeout=10) as response:
        if not 200<=response.status<300:raise ValueError('Notification not accepted')
def process(instance,snapshot,send=deliver):
    """Local alerts always work. External delivery is explicit and unprivileged."""
    import fcntl
    codes=alerts(snapshot)
    config=instance/'.notification-config.json';state=instance/'.notification-state.json'
    result={'active':codes,'delivery':'disabled'}
    # The health service may run as root for SMART. Do not consume user-writable
    # network configuration or send any external request from that context.
    if os.geteuid()==0:return result
    lock=instance/'.notification.lock'
    with lock.open('a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX)
        if not config.exists():return result
        try:
            cfg=private_read(config,os.getuid())
            if set(cfg)!={'url','token','enabled'} or cfg['enabled'] is not True:raise ValueError('Invalid consent')
            private_url(cfg['url'])
            old=private_read(state,os.getuid()) if state.exists() else {}
            stamp=now()
            last=dt.datetime.fromisoformat(old['at']) if old else None
            if not codes and not old:return {**result,'delivery':'ready'}
            if old.get('active')==codes and last and stamp-last<dt.timedelta(hours=24):return {**result,'delivery':'ready'}
            # Avoid duplicate bursts during repeated failures/restarts.
            if last and stamp-last<dt.timedelta(minutes=15):return {**result,'delivery':'ready'}
            send(cfg['url'],cfg['token'],codes)
            atomic(state,{'active':codes,'at':stamp.isoformat()})
            return {**result,'delivery':'sent'}
        except (OSError,ValueError,KeyError,TypeError):return {**result,'delivery':'review'}
