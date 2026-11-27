"""Build a private per-appliance media extension. No owner infrastructure URLs or accounts."""
import ipaddress,json,re,secrets
from urllib.parse import urlsplit
SLSKD='ghcr.io/slskd/slskd:0.26.2@sha256:d0963a3e5b16facd295bf4f2156dad0182f246b1b21a032cae12f5494c694843'
# slskd 0.26.2 reports socket connectivity and authenticated login separately.
SOULSEEK_LOGIN_PROBE = """
const response = await fetch(process.env.SLSKD_URL + '/api/v0/server', {
  headers: { 'X-API-Key': process.env.SLSKD_API_KEY },
  signal: AbortSignal.timeout(5000),
});
if (!response.ok) process.exit(1);
const { isConnected, isLoggedIn } = await response.json();
process.exit(isConnected === true && isLoggedIn === true ? 0 : 1);
"""
def token():return secrets.token_hex(24)
def invidious_credentials():
    # The pinned frontend requires a companion key of exactly 16 characters.
    alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return {'db':token(),'hmac':token(),'companion':''.join(secrets.choice(alphabet) for _ in range(16))}

def credentials():
    return {'username':'jobbi-'+secrets.token_hex(8),'password':token(),'api_key':token(),'ui_password':token()}
def pinned(image,repo):
    if not isinstance(image,str) or not re.fullmatch(re.escape(repo)+r'(?::[A-Za-z0-9._-]+)?@sha256:[a-f0-9]{64}',image):raise ValueError('Require reviewed exact image from '+repo)
    return image
def soulseek(i,uid,gid,c):
    for k in ('username','password','api_key','ui_password'):
        if not re.fullmatch('[a-z0-9-]{16,80}',c[k]):raise ValueError('Invalid generated provider credential')
    return {'slskd':{'build':{'context':'./security-patches','dockerfile':'Dockerfile.slskd','args':{'BASE_IMAGE':SLSKD}},'user':str(uid)+':'+str(gid),'restart':'unless-stopped','environment':{'SLSKD_SLSK_USERNAME':c['username'],'SLSKD_SLSK_PASSWORD':c['password'],'SLSKD_API_KEY':c['api_key'],'SLSKD_USERNAME':'jobbi-local','SLSKD_PASSWORD':c['ui_password'],'SLSKD_NO_HTTPS':'true','SLSKD_REMOTE_CONFIGURATION':'false','SLSKD_SHARED_DIR':'/shares','SLSKD_DOWNLOADS_DIR':'/downloads','SLSKD_INCOMPLETE_DIR':'/incomplete'},'volumes':[str(i/'data/pilot-media/slskd')+':/app',str(i/'data/pilot-media/shares')+':/shares:ro',str(i/'data/pilot-media/downloads')+':/downloads',str(i/'data/pilot-media/incomplete')+':/incomplete'],'cap_drop':['ALL'],'security_opt':['no-new-privileges:true'],'mem_limit':'512m'},'jobbi-music':{'environment':{'SLSKD_URL':'http://slskd:5030','SLSKD_API_KEY':c['api_key']}}}
def invidious_builds(images, context='./security-patches'):
    return {
        'invidious': {'build': {'context': context, 'dockerfile': 'Dockerfile.invidious',
                               'args': {'BASE_IMAGE': pinned(images['invidious'],'quay.io/invidious/invidious')}}},
        'invidious-db': {'build': {
            'context': context, 'dockerfile': 'Dockerfile.postgres', 'target': 'debian_patched',
            'args': {'BASE_IMAGE': pinned(images['postgres'],'docker.io/library/postgres'),
                     'DEBIAN_CODENAME': 'bookworm',
                     'PACKAGE_FLOORS': ' '.join(
                         name+'=1.5.2-6+deb12u3' for name in
                         ('libpam-modules','libpam-modules-bin','libpam-runtime','libpam0g'))}}},
        'invidious-companion': {'image': pinned(images['companion'],'quay.io/invidious/invidious-companion')},
    }

def invidious(i,images,source,secret):
    # The source tree must contain the reviewed upstream DB initialization files.
    builds=invidious_builds(images)
    if not all(re.fullmatch('[a-f0-9]{48}',secret[k]) for k in ('db','hmac')) or not re.fullmatch('[A-Za-z0-9]{16}',secret['companion']) or len(set(secret.values()))!=3:raise ValueError('Independent generated secrets required')
    cfg={'db':{'dbname':'invidious','user':'invidious','password':secret['db'],'host':'invidious-db','port':5432},'check_tables':True,'hmac_key':secret['hmac'],'invidious_companion':[{'private_url':'http://invidious-companion:8282/companion'}],'invidious_companion_key':secret['companion'],'registration_enabled':False,'statistics_enabled':False}
    return {'services':{
      'invidious':{**builds['invidious'],'restart':'unless-stopped','ports':['127.0.0.1:18091:3000'],'environment':{'INVIDIOUS_CONFIG':json.dumps(cfg)},'depends_on':{'invidious-db':{'condition':'service_healthy'},'invidious-companion':{'condition':'service_started'}}},
      'invidious-companion':{**builds['invidious-companion'],'restart':'unless-stopped','environment':{'SERVER_SECRET_KEY':secret['companion']},'cap_drop':['ALL'],'security_opt':['no-new-privileges:true'],'read_only':True,'volumes':['pilot-invidious-companion-cache:/var/tmp/youtubei.js:rw']},
      'invidious-db':{**builds['invidious-db'],'restart':'unless-stopped','environment':{'POSTGRES_DB':'invidious','POSTGRES_USER':'invidious','POSTGRES_PASSWORD':secret['db']},'healthcheck':{'test':['CMD','pg_isready','-h','127.0.0.1','-U','invidious','-d','invidious'],'interval':'5s','timeout':'3s','retries':30},'volumes':['pilot-invidious-db:/var/lib/postgresql/data',str(source/'docker/init-invidious-db.sh')+':/docker-entrypoint-initdb.d/init-invidious-db.sh:ro',str(source/'config/sql')+':/config/sql:ro']}
    },'volumes':{'pilot-invidious-db':{},'pilot-invidious-companion-cache':{}}}

def public_origin(raw):
    u=urlsplit(raw)
    if u.scheme!='https' or u.username or u.password or u.query or u.fragment or u.path not in ('','/') or not u.hostname or not u.port:raise ValueError('Require exact approved HTTPS Invidious origin')
    try:
        ip=ipaddress.IPv4Address(u.hostname)
        valid=any(ip in ipaddress.IPv4Network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')) and u.port==18091
    except ValueError:
        valid=bool(re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+\.ts\.net',u.hostname)) and 1024<=u.port<=65535
    if not valid or u.netloc!=u.hostname+':'+str(u.port):raise ValueError('Require own private lab or tailnet origin')
    return u.scheme+'://'+u.netloc
def local_fallback_source(source):
    # The upstream commercial patch disables external fallback. Only the fixed
    # instance-local service may be used; the customer-facing URL is separate.
    anchor='  const raw=[env.INVIDIOUS_URL'
    if source.count(anchor)!=1 or source.count('normalizeInvidiousResults(raw,origin)')!=1:raise ValueError('Unexpected pinned Invidious search adapter')
    return source.replace(anchor,"  if(env.JOBBI_LOCAL_INVIDIOUS==='true')return ['http://invidious:3000'];\n"+anchor).replace('normalizeInvidiousResults(raw,origin)',"normalizeInvidiousResults(raw,origin==='http://invidious:3000'?process.env.JOBBI_INVIDIOUS_PUBLIC_ORIGIN:origin)").replace('Check your yt.jobbisoft.com.mx /api/v1/search endpoint.','Check your own Invidious service.')
