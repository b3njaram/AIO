"""Journal only non-secret Nextcloud HTTPS config. Never trust a broad proxy network."""
import json,re,subprocess,ipaddress
from urllib.parse import urlsplit
from pathlib import Path
from private_origins import atomic_write
KEYS=('trusted_domains','overwritehost','overwriteprotocol','overwrite.cli.url')
def occ(instance,*args):
    return subprocess.check_output(['bash',str(Path(__file__).with_name('ctl.sh')),str(instance),'exec','-T','-u','www-data','nextcloud','php','occ',*args],text=True,stderr=subprocess.DEVNULL,timeout=60)
def read(instance):
    raw=json.loads(occ(instance,'config:list','system'))['system']
    if raw.get('installed') is not True:raise ValueError('Nextcloud must be installed')
    if raw.get('trusted_proxies') or raw.get('overwritecondaddr'):raise ValueError('Existing custom proxy configuration requires manual review')
    result={k:raw.get(k) for k in KEYS}
    if not isinstance(result['trusted_domains'],list) or any(not isinstance(x,str) or '*' in x for x in result['trusted_domains']):raise ValueError('Review existing trusted domains')
    return result
def desired(before,url,allow_lab=False):
    u=urlsplit(url)
    lab=False
    if allow_lab:
        try:lab=any(ipaddress.IPv4Address(u.hostname) in ipaddress.IPv4Network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))
        except (ValueError,TypeError):pass
    if u.scheme!='https' or not u.hostname or not (u.hostname.endswith('.ts.net') or lab) or u.username or u.password or u.path or u.query or u.fragment or not re.fullmatch(r'[a-z0-9.-]+:\d+',u.netloc):raise ValueError('Use exact approved private Nextcloud HTTPS origin')
    return {**before,'trusted_domains':list(dict.fromkeys(before['trusted_domains']+[u.netloc])),'overwritehost':u.netloc,'overwriteprotocol':'https','overwrite.cli.url':url}
def set_scalar(instance,key,value):
    if value is None:occ(instance,'config:system:delete',key)
    else:occ(instance,'config:system:set',key,'--value='+value)
def prepare(instance,url,allow_lab=False):
    journal=instance/'.nextcloud-origin.json'
    if journal.exists():raise ValueError('Existing Nextcloud origin journal')
    before=read(instance);after=desired(before,url,allow_lab)
    atomic_write(journal,json.dumps({'before':before,'after':after}).encode(),0o600)
    if before['trusted_domains']!=after['trusted_domains']:
        occ(instance,'config:system:set','trusted_domains',str(len(before['trusted_domains'])),'--value='+after['trusted_domains'][-1])
    for key in KEYS[1:]:
        if before[key]!=after[key]:set_scalar(instance,key,after[key])
    verify(instance,url,allow_lab)
def verify(instance,url,allow_lab=False):
    current=read(instance)
    if current!=desired(current,url,allow_lab):raise ValueError('Nextcloud private HTTPS configuration not applied')
def rollback(instance):
    journal=instance/'.nextcloud-origin.json'
    if not journal.exists():return
    state=json.loads(journal.read_text());before,after=state['before'],state['after'];current=read(instance)
    if any(current[k] not in (before[k],after[k]) for k in KEYS):raise ValueError('Nextcloud changed after preparation; review before rollback')
    for key in KEYS[1:]:
        if current[key]!=before[key]:set_scalar(instance,key,before[key])
    if current['trusted_domains']!=before['trusted_domains']:
        occ(instance,'config:system:delete','trusted_domains',str(len(before['trusted_domains'])))
    if read(instance)!=before:raise ValueError('Nextcloud rollback verification failed')
    journal.unlink()
