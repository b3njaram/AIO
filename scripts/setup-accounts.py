#!/usr/bin/env python3
"""Local guided account setup. No passwords in files, logs or HTTP-facing Jobbi endpoints."""
import argparse,getpass,http.cookiejar,json,re,subprocess,sys,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOCAL=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def request(base,path,payload=None,opener=None):
    headers={'Accept':'application/json','Origin':base}
    raw=None
    if payload is not None:headers['Content-Type']='application/json';raw=json.dumps(payload).encode()
    q=urllib.request.Request(base+path,data=raw,headers=headers)
    try:r=(opener or LOCAL).open(q,timeout=20)
    except urllib.error.HTTPError as e:r=e
    with r:
        data=r.read(1024*1024)
        try:body=json.loads(data)
        except ValueError:body={}
        return r.status,body
def require(ok,message):
    if not ok:raise ValueError(message)
def password(app):
    pw=getpass.getpass(app+' password (12+ characters): ')
    require(len(pw)>=12 and pw==getpass.getpass('Confirm password: '),'Password mismatch or too short')
    return pw
def env_for(instance):
    env=dict(x.split('=',1) for x in (instance/'.env').read_text().splitlines() if '=' in x)
    require(env.get('INSTANCE_DIR')==str(instance) and env.get('BIND_IP')=='127.0.0.1' and re.fullmatch('jobbi-[a-z0-9-]+',env.get('COMPOSE_PROJECT_NAME','')),'Use a local isolated customer instance')
    require(env.get('MUSIC_HTTPS')!='true' and env.get('MOVIE_HTTPS')!='true','Complete initial account setup before enabling private HTTPS')
    return env
def _create(instance,app,user,email,pw):
    env=env_for(instance)
    selected=set(env['COMPOSE_PROFILES'].split(','))
    require(app in selected,'Application is not installed')
    require(re.fullmatch(r'[A-Za-z0-9_.-]{1,48}',user) and re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email),'Invalid owner username/email')
    def base(port):return 'http://127.0.0.1:'+env[port]
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(instance)]
    def cmd(*a):return subprocess.run(ctl+list(a),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=180).returncode
    if app=='music':
        user=env['MUSIC_ADMIN'];url=base('MUSIC_PORT');jar=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        login=lambda:request(url,'/api/login',{'username':user,'password':pw},jar)
        code,body=login()
        if code!=200:
            code,_=request(base('NAV_PORT'),'/auth/createAdmin',{'username':user,'password':pw})
            require(code in (200,201),'Navidrome owner creation refused; existing account was not changed')
            code,body=login()
        require(code==200 and body.get('admin') is True,'Music owner login not confirmed')
        if body.get('csrfToken'):
            q=urllib.request.Request(url+'/api/logout',data=b'{}',headers={'Origin':url,'Content-Type':'application/json','X-CSRF-Token':body['csrfToken']})
            with jar.open(q,timeout=20):pass
    elif app=='photos':
        url=base('PHOTO_PORT');login=lambda:request(url,'/api/auth/login',{'email':email,'password':pw})
        code,body=login()
        if code not in (200,201):
            code,_=request(url,'/api/auth/admin-sign-up',{'email':email,'password':pw,'name':user})
            require(code in (200,201),'Photo owner creation refused; existing account was not changed')
            code,body=login()
        require(code in (200,201) and body.get('isAdmin') is True,'Photo owner login not confirmed')
    elif app=='movies':
        url=base('MOVIE_PORT');login=lambda:request(url,'/api/auth/login',{'username':user,'password':pw,'remember':False})
        code,body=login()
        if code!=200:
            # Upstream create-user.js also resets existing passwords; use a
            # guarded SQLite transaction that refuses ANY pre-existing users.
            script="""import { db, getUserByUsername, createUser, ensureDefaultProfile } from './db.js';
import { hashPassword } from './auth.js';
import fs from 'node:fs';
const {username,password}=JSON.parse(fs.readFileSync(0,'utf8'));
db.transaction(()=>{
  if(db.prepare('SELECT COUNT(*) n FROM users').get().n!==0)throw Error('Existing users; no changes made');
  createUser(username,hashPassword(password));
  ensureDefaultProfile(getUserByUsername(username));
}).immediate();"""
            result=subprocess.run(ctl+['exec','-T','backend','node','--input-type=module','-e',script],input=json.dumps({'username':user,'password':pw}),text=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=60)
            require(result.returncode==0,'Movie first owner creation refused; no existing password reset')
            code,body=login()
        require(code==200 and body.get('isAdmin') is True,'Movie owner login not confirmed')
    elif app=='tasks':
        require(env['TASK_REGISTRATION']=='false','Registration must be disabled')
        url=base('TASK_PORT');code,info=request(url,'/api/v1/info')
        require(code==200 and info.get('auth',{}).get('local',{}).get('registration_enabled') is False,'Task registration not confirmed closed')
        login=lambda:request(url,'/api/v1/login',{'username':user,'password':pw})
        code,body=login()
        if code!=200:
            require(cmd('exec','-T','vikunja','/app/vikunja/vikunja','user','create','--username',user,'--email',email,'--password',pw)==0,'Task owner creation refused; existing account unchanged')
            code,body=login()
        require(code==200 and bool(body.get('token')),'Task login not confirmed')
    elif app=='monitor':
        try:import socketio
        except ImportError:raise ValueError('Install python3-socketio on the dedicated Ubuntu appliance')
        client=socketio.Client(reconnection=False,request_timeout=10)
        try:
            client.connect(base('MONITOR_PORT'),transports=['websocket'],wait_timeout=15)
            login=lambda:client.call('login',{'username':user,'password':pw},timeout=20)
            from kuma_ready import setup_required
            if setup_required(client,socketio):
                require(client.call('setup',(user,pw),timeout=20).get('ok'),'Monitor setup refused; existing account unchanged')
            result=login()
            require(result.get('ok'),'Monitor owner login not confirmed')
        finally:
            if client.connected:client.disconnect()
    elif app=='files':
        url=base('CLOUD_PORT');code,info=request(url,'/status.php')
        require(code==200 and isinstance(info.get('installed'),bool),'Nextcloud status unknown')
        if not info['installed']:
            require(cmd('exec','-T','-u','www-data','nextcloud','php','occ','maintenance:install','--database=pgsql','--database-host=nextcloud-db','--database-name=nextcloud','--database-user=nextcloud','--database-pass='+env['CLOUD_DB_PASSWORD'],'--admin-user='+user,'--admin-pass='+pw)==0,'Nextcloud install failed; inspect locally')
            require(cmd('exec','-T','-u','www-data','nextcloud','php','occ','config:system:set','trusted_domains','1','--value=127.0.0.1')==0,'Nextcloud local origin not configured')
        import base64
        q=urllib.request.Request(url+'/remote.php/dav/files/'+user+'/',method='PROPFIND',headers={'Authorization':'Basic '+base64.b64encode((user+':'+pw).encode()).decode(),'Depth':'0'})
        try:
            with LOCAL.open(q,timeout=20) as r:require(r.status==207,'Nextcloud WebDAV authentication not confirmed')
        except urllib.error.HTTPError as e:raise ValueError('Nextcloud WebDAV authentication refused (HTTP '+str(e.code)+')') from None
    else:raise ValueError('Use the app native setup for this service')
def create(instance,app,user,email,pw):
    _create(instance,app,user,email,pw)
    from account_progress import record
    record(instance,app)
    if app=='monitor':
        # Best-effort initial fixed monitors; a valid owner login remains valid
        # even if a monitor creation fails. No passwords are retained.
        try:
            import importlib.util
            spec=importlib.util.spec_from_file_location('monitors',ROOT/'scripts/configure-monitors.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
            env,desired=m.targets(instance);m.configure(env,desired,user,pw,True)
            print('Default appliance monitors configured',flush=True)
        except Exception:
            print('Default monitor creation needs review; owner login verified',flush=True)
def invite_vault(instance,email):
    """Send only the intended customer invitation; native client creates encryption keys."""
    import urllib.parse
    env=env_for(instance)
    require('passwords' in env['COMPOSE_PROFILES'].split(','),'Vaultwarden is not installed')
    require(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email),'Invalid owner email')
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(instance)]
    cid=subprocess.check_output(ctl+['ps','-q','vaultwarden'],text=True).strip()
    require(bool(cid),'Vaultwarden not running')
    obj=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
    actual=dict(x.split('=',1) for x in obj['Config']['Env'] if '=' in x)
    require(actual.get('SIGNUPS_ALLOWED')=='false','Vaultwarden public registration not disabled')
    require(actual.get('ADMIN_TOKEN')==env['VAULT_ADMIN_TOKEN'],'Vaultwarden admin token differs; review locally')
    base='http://127.0.0.1:'+env['VAULT_PORT']
    admin=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    req=urllib.request.Request(base+'/admin/',data=urllib.parse.urlencode({'token':env['VAULT_ADMIN_TOKEN']}).encode(),headers={'Content-Type':'application/x-www-form-urlencoded','Origin':base})
    with admin.open(req,timeout=20) as r:require(r.status==200,'Vaultwarden admin login not confirmed')
    code,_=request(base,'/admin/invite',{'email':email},admin)
    require(code==200,'Vaultwarden invitation refused; inspect the existing owner invitation locally')
    from account_progress import record
    record(instance,'passwords','invited')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--username',default='owner');p.add_argument('--email',required=True);p.add_argument('--apps',default='music,movies,photos,files,tasks,monitor');p.add_argument('--invite-vault',action='store_true',help='Explicitly invite this customer email; customer creates master password in native client');p.add_argument('--shared-password',action='store_true',help='Explicitly use one password for selected apps; unique passwords recommended');p.add_argument('--apply',action='store_true');a=p.parse_args()
    i=a.instance.resolve();env=env_for(i)
    selected=[x for x in a.apps.split(',') if x in env['COMPOSE_PROFILES'].split(',')]
    require(all(x in ('music','movies','photos','files','tasks','monitor') for x in selected),'Unsupported automated app')
    print('Selected accounts:',', '.join(selected))
    print('Vaultwarden master-password creation and customer Tailscale enrollment remain native setup steps. Passwords are prompted separately unless --shared-password is selected; trusted Docker admins may see CLI arguments transiently.')
    if not a.apply:return
    if not sys.stdin.isatty():p.error('Use a trusted interactive terminal; passwords must not be echoed or piped')
    import os,fcntl
    os.umask(0o077)
    with (i/'.account-setup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        shared=password('Shared owner') if a.shared_password and selected else None
        failed=[]
        for app in selected:
            try:
                create(i,app,a.username,a.email,shared if shared is not None else password(app))
                print(app+': owner login verified; functional acceptance still pending.')
            except (OSError,ValueError,KeyError,subprocess.SubprocessError,RuntimeError):
                failed.append(app);print(app+': needs individual review; existing passwords not reset.')
        if a.invite_vault:
            invite_vault(i,a.email)
            print('Vaultwarden owner invited. Finish encryption setup in the native HTTPS client.')
    print('Run onboard.py for actual functional acceptance; login verification is shown separately.')
    if failed:sys.exit('Account steps needing review: '+', '.join(failed))
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Account setup stopped: '+type(e).__name__+'; review local app state and credentials. No password printed.')
