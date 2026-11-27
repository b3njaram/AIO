"""Build a private per-appliance media extension. No owner infrastructure URLs or accounts."""
import ipaddress,json,re,secrets
from urllib.parse import urlsplit
SLSKD='ghcr.io/slskd/slskd:0.26.2@sha256:d0963a3e5b16facd295bf4f2156dad0182f246b1b21a032cae12f5494c694843'
def token():return secrets.token_hex(24)
def credentials():
    return {'username':'jobbi-'+secrets.token_hex(8),'password':token(),'api_key':token(),'ui_password':token()}
def pinned(image,repo):
    if not isinstance(image,str) or not re.fullmatch(re.escape(repo)+r'(?::[A-Za-z0-9._-]+)?@sha256:[a-f0-9]{64}',image):raise ValueError('Require reviewed exact image from '+repo)
    return image
def soulseek(i,uid,gid,c):
    for k in ('username','password','api_key','ui_password'):
        if not re.fullmatch('[a-z0-9-]{16,80}',c[k]):raise ValueError('Invalid generated provider credential')
    return {'slskd':{'image':SLSKD,'user':str(uid)+':'+str(gid),'restart':'unless-stopped','environment':{'SLSKD_SLSK_USERNAME':c['username'],'SLSKD_SLSK_PASSWORD':c['password'],'SLSKD_API_KEY':c['api_key'],'SLSKD_USERNAME':'jobbi-local','SLSKD_PASSWORD':c['ui_password'],'SLSKD_NO_HTTPS':'true','SLSKD_REMOTE_CONFIGURATION':'false','SLSKD_SHARED_DIR':'/shares','SLSKD_DOWNLOADS_DIR':'/downloads','SLSKD_INCOMPLETE_DIR':'/incomplete'},'volumes':[str(i/'data/pilot-media/slskd')+':/app',str(i/'data/pilot-media/shares')+':/shares:ro',str(i/'data/pilot-media/downloads')+':/downloads',str(i/'data/pilot-media/incomplete')+':/incomplete'],'cap_drop':['ALL'],'security_opt':['no-new-privileges:true'],'mem_limit':'512m'},'jobbi-music':{'environment':{'SLSKD_URL':'http://slskd:5030','SLSKD_API_KEY':c['api_key']}}}
def invidious(i,images,source,secret):
    # The source tree must contain the reviewed upstream DB initialization files.
    iv=pinned(images['invidious'],'quay.io/invidious/invidious')
    companion=pinned(images['companion'],'quay.io/invidious/invidious-companion')
    db=pinned(images['postgres'],'docker.io/library/postgres')
    if not all(re.fullmatch('[a-f0-9]{48}',secret[k]) for k in ('db','hmac','companion')) or len(set(secret.values()))!=3:raise ValueError('Independent generated secrets required')
    cfg={'db':{'dbname':'invidious','user':'invidious','password':secret['db'],'host':'invidious-db','port':5432},'check_tables':True,'hmac_key':secret['hmac'],'invidious_companion':[{'private_url':'http://invidious-companion:8282/companion'}],'invidious_companion_key':secret['companion'],'registration_enabled':False,'statistics_enabled':False}
    return {'services':{
      'invidious':{'image':iv,'restart':'unless-stopped','ports':['127.0.0.1:18091:3000'],'environment':{'INVIDIOUS_CONFIG':json.dumps(cfg)},'depends_on':['invidious-db','invidious-companion']},
      'invidious-companion':{'image':companion,'restart':'unless-stopped','environment':{'SERVER_SECRET_KEY':secret['companion']},'cap_drop':['ALL'],'security_opt':['no-new-privileges:true']},
      'invidious-db':{'image':db,'restart':'unless-stopped','environment':{'POSTGRES_DB':'invidious','POSTGRES_USER':'invidious','POSTGRES_PASSWORD':secret['db']},'volumes':['pilot-invidious-db:/var/lib/postgresql/data',str(source/'docker/init-invidious-db.sh')+':/docker-entrypoint-initdb.d/init-invidious-db.sh:ro',str(source/'config/sql')+':/config/sql:ro']}
    },'volumes':{'pilot-invidious-db':{}}}
