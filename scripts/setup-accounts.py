#!/usr/bin/env python3
"""Local guided account setup. No passwords in files, logs or HTTP-facing Jobbi endpoints."""
import argparse,getpass,http.cookiejar,json,re,subprocess,sys,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def request(base,path,payload=None,opener=None):
    headers={'Accept':'application/json','Origin':base}
    raw=None
    if payload is not None:headers['Content-Type']='application/json';raw=json.dumps(payload).encode()
    q=urllib.request.Request(base+path,data=raw,headers=headers)
    try:r=(opener or urllib.request).open(q,timeout=20)
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
def create(instance,app,user,email,pw):
    env=env_for(instance)
    selected=set(env['COMPOSE_PROFILES'].split(','))
    require(app in selected,'Application is not installed')
    require(re.fullmatch(r'[A-Za-z0-9_.-]{1,48}',user) and re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email),'Invalid owner username/email')
    def base(port):return 'http://127.0.0.1:'+env[port]
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(instance)]
    def cmd(*a):return subprocess.run(ctl+list(a),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=180).returncode
    if app=='music':
        user=env['MUSIC_ADMIN'];url=base('MUSIC_PORT');jar=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
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
        if code!=200:
            code,_=request(url,'/api/auth/admin-sign-up',{'email':email,'password':pw,'name':user})
            require(code in (200,201),'Photo owner creation refused; existing account was not changed')
            code,body=login()
        require(code in (200,201) and body.get('isAdmin') is True,'Photo owner login not confirmed')
    elif app=='movies':
        url=base('MOVIE_PORT');login=lambda:request(url,'/api/auth/login',{'username':user,'password':pw,'remember':False})
        code,body=login()
        if code!=200:
            # Refuse overwrite by checking the pinned application's user database CLI
            # only on a newly initialized instance with no account-creation journal.
            require(not (instance/'.account-movies-attempted').exists(),'Prior movie setup attempted; verify existing credentials manually')
            (instance/'.account-movies-attempted').touch(mode=0o600,exist_ok=False)
            require(cmd('exec','-T','backend','node','create-user.js',user,pw)==0,'Movie user creation failed; inspect locally')
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
    elif app=='files':
        url=base('CLOUD_PORT');code,info=request(url,'/status.php')
        require(code==200 and isinstance(info.get('installed'),bool),'Nextcloud status unknown')
        if not info['installed']:
            require(cmd('exec','-T','-u','www-data','nextcloud','php','occ','maintenance:install','--database=pgsql','--database-host=nextcloud-db','--database-name=nextcloud','--database-user=nextcloud','--database-pass='+env['CLOUD_DB_PASSWORD'],'--admin-user='+user,'--admin-pass='+pw)==0,'Nextcloud install failed; inspect locally')
        import base64
        q=urllib.request.Request(url+'/remote.php/dav/files/'+user+'/',method='PROPFIND',headers={'Authorization':'Basic '+base64.b64encode((user+':'+pw).encode()).decode(),'Depth':'0'})
        try:
            with urllib.request.urlopen(q,timeout=20) as r:require(r.status==207,'Nextcloud WebDAV authentication not confirmed')
        except urllib.error.HTTPError as e:raise ValueError('Nextcloud WebDAV authentication refused (HTTP '+str(e.code)+')') from None
    else:raise ValueError('Use the app native setup for this service')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--username',default='owner');p.add_argument('--email',required=True);p.add_argument('--apps',default='music,movies,photos,files,tasks');p.add_argument('--apply',action='store_true');a=p.parse_args()
    i=a.instance.resolve();env=env_for(i)
    selected=[x for x in a.apps.split(',') if x in env['COMPOSE_PROFILES'].split(',')]
    require(all(x in ('music','movies','photos','files','tasks') for x in selected),'Unsupported automated app')
    print('Selected accounts:',', '.join(selected))
    print('Vaultwarden, Uptime Kuma and customer Tailscale enrollment remain native setup steps. Passwords are prompted separately; trusted Docker admins may see CLI arguments transiently.')
    if not a.apply:return
    import os,fcntl
    os.umask(0o077)
    with (i/'.account-setup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for app in selected:
            create(i,app,a.username,a.email,password(app))
            print(app+': owner login verified; functional acceptance still pending.')
    print('Run onboard.py for remaining setup and actual acceptance; no automatic confirmation is recorded.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Account setup stopped: '+type(e).__name__+'; review local app state and credentials. No password printed.')
