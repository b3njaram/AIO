#!/usr/bin/env python3
"""CI-only synthetic audio/photo fixtures; verify credentials, content and restored state."""
import argparse,datetime as dt,hashlib,http.cookiejar,json,os,secrets,struct,subprocess,time,urllib.error,urllib.parse,urllib.request,zlib
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('account_setup',Path(__file__).with_name('setup-accounts.py'))
account_setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(account_setup)
ROOT=Path(__file__).resolve().parents[1]
def check(ok,message):
    if not ok:raise AssertionError(message)
def request(base,path,method='GET',data=None,headers=None,opener=None):
    h={'Accept':'application/json',**(headers or {})}
    if isinstance(data,dict):h['Content-Type']='application/json';data=json.dumps(data).encode()
    q=urllib.request.Request(base+path,data=data,headers=h,method=method)
    try:r=(opener or urllib.request).open(q,timeout=30) if opener else urllib.request.urlopen(q,timeout=30)
    except urllib.error.HTTPError as e:r=e
    with r:return r.status,r.read()
def js(base,path,method='GET',data=None,headers=None,opener=None,expected=(200,201)):
    status,body=request(base,path,method,data,headers,opener)
    check(status in expected,f'{path}: unexpected HTTP {status}')
    return json.loads(body)
def wait(fn,seconds=120):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            result=fn()
            if result:return result
        except (OSError,ValueError,AssertionError):pass
        time.sleep(3)
    raise RuntimeError('Service or data not ready before deadline')
def png():
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    w=h=32;pixels=(b'\x00'+b'\x28\x91\xd2'*w)*h
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
def multipart(fields,payload):
    b='jobbi-'+secrets.token_hex(12);parts=[]
    for k,v in fields.items():parts.append(('--'+b+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+v+'\r\n').encode())
    parts.append(('--'+b+'\r\nContent-Disposition: form-data; name="assetData"; filename="jobbi-pilot.png"\r\nContent-Type: image/png\r\n\r\n').encode()+payload+b'\r\n')
    return b''.join(parts)+('--'+b+'--\r\n').encode(),'multipart/form-data; boundary='+b
def music(env,instance,fixture,recover):
    nav='http://127.0.0.1:'+env['NAV_PORT'];base='http://127.0.0.1:'+env['MUSIC_PORT']
    songfile=instance/'data/music/Jobbi Pilot Tone.mp3'
    user=env['MUSIC_ADMIN'];pw=fixture['music_password']
    wait(lambda:request(nav,'/')[0]==200)
    if not recover:
        subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','3','-metadata','title=Jobbi Pilot Tone','-metadata','artist=Jobbi Synthetic','-metadata','album=Jobbi Pilot','-c:a','libmp3lame',str(songfile)],check=True)
        fixture['music_sha']=hashlib.sha256(songfile.read_bytes()).hexdigest()
        wait(lambda:request(base,'/api/status')[0] in (200,401))
        account_setup.create(instance,'music',user,'pilot@example.invalid',pw)
        check(request(nav,'/auth/createAdmin','POST',{'username':'other-pilot','password':secrets.token_urlsafe(24)})[0]==403,'Second initial admin creation not denied')
    check(hashlib.sha256(songfile.read_bytes()).hexdigest()==fixture['music_sha'],'Audio file changed')
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    # Compose starts the music API after its database. Navidrome readiness alone
    # does not guarantee that this separate HTTP listener can accept requests.
    def anonymous_status():
        status,_=request(base,'/api/search?q=Jobbi')
        return status if status<500 else None
    check(wait(anonymous_status)==401,'Anonymous music search did not return HTTP 401')
    login=js(base,'/api/login','POST',{'username':user,'password':pw},{'Origin':base},opener)
    check(login.get('admin') is True,'Expected customer admin')
    h={'Origin':base,'X-CSRF-Token':login['csrfToken']}
    if not recover:js(base,'/api/library/scan','POST',{},h,opener)
    def song():
        rows=js(base,'/api/search?q=Jobbi%20Pilot%20Tone',headers=h,opener=opener).get('song',[])
        return next((x for x in rows if x.get('title')=='Jobbi Pilot Tone'),None)
    found=wait(song);sid=found['id'];quoted=urllib.parse.quote(sid,safe='')
    status,raw=request(base,'/api/download/song/'+quoted,headers=h,opener=opener)
    check(status==200 and hashlib.sha256(raw).hexdigest()==fixture['music_sha'],'Original audio download differs')
    status,stream=request(base,'/api/stream/'+quoted+'?quality=original',headers=h,opener=opener)
    check(status==200 and hashlib.sha256(stream).hexdigest()==fixture['music_sha'],'Original audio stream differs')
    if not recover:
        js(base,'/api/star','POST',{'id':sid,'starred':True},h,opener)
        js(base,'/api/playlists','POST',{'name':'Jobbi synthetic playlist'},h,opener)
        pl=next(x for x in js(base,'/api/playlists',headers=h,opener=opener) if x['name']=='Jobbi synthetic playlist')
        js(base,'/api/playlists/'+urllib.parse.quote(pl['id'],safe=''),'PATCH',{'addSongId':sid,'public':False},h,opener)
        playlist_path='/api/playlists/'+urllib.parse.quote(pl['id'],safe='')
        check(js(base,playlist_path,'PATCH',{'public':True},h,opener)['playlist']['public'] is True,'Public visibility change not confirmed')
        check(js(base,playlist_path,'PATCH',{'public':False},h,opener)['playlist']['public'] is False,'Private visibility change not confirmed')
        listed=next(x for x in js(base,'/api/playlists',headers=h,opener=opener) if x['id']==pl['id'])
        check(listed.get('public') is False,'Private visibility omitted in listing')
        fixture['playlist_id']=pl['id']
    starred=js(base,'/api/starred',headers=h,opener=opener)
    check(any(x['id']==sid for x in starred.get('song',[])),'Favorite missing')
    playlist=js(base,'/api/playlists/'+urllib.parse.quote(fixture['playlist_id'],safe=''),headers=h,opener=opener)
    check(any(x['id']==sid for x in playlist.get('entry',[])) and playlist.get('public') is False,'Private playlist content missing')
    js(base,'/api/logout','POST',{},h,opener)
    check(request(base,'/api/download/song/'+quoted,opener=opener)[0]==401,'Music available after logout')
    print('PASS: '+('restored ' if recover else '')+'music login, scan/search, complete audio stream/download, favorite, private playlist and logout')
def photos(env,instance,fixture,recover):
    base='http://127.0.0.1:'+env['PHOTO_PORT']+'/api'
    wait(lambda:request(base,'/server/ping')[0]==200)
    email=fixture['photo_email'];pw=fixture['photo_password']
    if not recover:
        account_setup.create(instance,'photos','owner',email,pw)
        code,_=request(base,'/auth/admin-sign-up','POST',{'email':'another@example.invalid','password':secrets.token_urlsafe(24),'name':'Other synthetic'})
        check(400<=code<500,'Second photo admin creation not denied')
    login=js(base,'/auth/login','POST',{'email':email,'password':pw})
    check(login.get('isAdmin') is True,'Expected photo admin')
    h={'Authorization':'Bearer '+login['accessToken']}
    payload=png()
    if not recover:
        date=dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z')
        raw,mime=multipart({'fileCreatedAt':date,'fileModifiedAt':date,'filename':'jobbi-pilot.png'},payload)
        result=js(base,'/assets','POST',raw,{**h,'Content-Type':mime})
        fixture['asset_id']=result['id']
    path='/assets/'+urllib.parse.quote(fixture['asset_id'],safe='')+'/original'
    check(request(base,path)[0] in (401,403),'Anonymous photo download not denied')
    code,body=request(base,path,headers=h)
    check(code==200 and body==payload,'Original photo bytes differ')
    print('PASS: '+('restored ' if recover else '')+'photo admin, authenticated original retrieval, anonymous denial and byte equality')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--recover',action='store_true');a=p.parse_args()
    i=a.instance.resolve();env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    check(os.getenv('GITHUB_ACTIONS')=='true' and i.parent==Path('/tmp/jobbi-library') and i.name in ('source','recovered') and env['INSTANCE_DIR']==str(i) and env['BIND_IP']=='127.0.0.1','Disposable CI instances only')
    path=Path('/tmp/jobbi-library-fixture.json')
    if a.recover:fixture=json.loads(path.read_text())
    else:
        check(not path.exists(),'Fixture already exists')
        fixture={'music_password':secrets.token_urlsafe(24),'photo_email':'pilot'+secrets.token_hex(4)+'@example.invalid','photo_password':secrets.token_urlsafe(24)}
    music(env,i,fixture,a.recover);photos(env,i,fixture,a.recover)
    if not a.recover:
        os.umask(0o077)
        with path.open('x') as out:json.dump(fixture,out)
if __name__=='__main__':main()
