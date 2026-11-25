#!/usr/bin/env python3
"""Synthetic media test for disposable CI instances only. Never run on a customer."""
import argparse,hashlib,http.cookiejar,json,os,secrets,subprocess,sys,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(*args):subprocess.run(args,check=True)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('instance',type=Path)
    p.add_argument('--fixture',type=Path,required=True,help='Private CI credentials file')
    p.add_argument('--recover',action='store_true')
    p.add_argument('--secure-cookie',action='store_true')
    a=p.parse_args()
    instance=a.instance.resolve(); env=dict(x.split('=',1) for x in (instance/'.env').read_text().splitlines() if '=' in x)
    if os.getenv('GITHUB_ACTIONS')!='true' or instance.parent!=Path('/tmp/jobbi-media') or instance.name not in ('source','recovered') or env.get('INSTANCE_DIR')!=str(instance) or env.get('BIND_IP')!='127.0.0.1':
        p.error('Only disposable GitHub Actions media pilot instances allowed')
    if a.fixture.resolve()!=Path('/tmp/jobbi-media-fixture.json'):p.error('Invalid fixture path')
    base='http://127.0.0.1:'+env['MOVIE_PORT']
    media=instance/'data/movies/media/Jobbi Pilot 2026.mp4'
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(instance)]
    if a.secure_cookie and not a.recover:p.error('Use the existing recovered fixture')
    if not a.recover:
        if a.fixture.exists() or media.exists():p.error('Existing fixture')
        username='pilot_'+secrets.token_hex(5); password=secrets.token_urlsafe(24)
        # Only disposable generated credentials, never logged by the test.
        run(*ctl,'exec','-T','backend','node','create-user.js',username,password)
        run('ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=blue:s=160x120:r=10','-t','2','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(media))
        os.umask(0o077)
        a.fixture.write_text(json.dumps({'username':username,'password':password,'sha256':hashlib.sha256(media.read_bytes()).hexdigest()}))
    f=json.loads(a.fixture.read_text())
    assert hashlib.sha256(media.read_bytes()).hexdigest()==f['sha256'],'Restored video differs'
    jar=http.cookiejar.CookieJar()
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    def call(path,data=None,headers=None,status=200):
        h={'Origin':base,'Accept':'application/json',**(headers or {})}
        b=None
        if data is not None:h['Content-Type']='application/json';b=json.dumps(data).encode()
        q=urllib.request.Request(base+path,data=b,headers=h)
        try:r=opener.open(q,timeout=20)
        except urllib.error.HTTPError as e:r=e
        with r:
            assert r.status==status,f'{path}: expected {status}, got {r.status}'
            return r.read()
    def js(path,data=None,headers=None):return json.loads(call(path,data,headers))
    call('/api/auth/me',status=401)
    login=js('/api/auth/login',{'username':f['username'],'password':f['password'],'remember':False})
    assert login['username']==f['username'] and login['isAdmin']
    if a.secure_cookie:
        session=next(c for c in jar if c.name=='sh_session')
        assert session.secure and session.has_nonstandard_attr('HttpOnly') and session.get_nonstandard_attr('SameSite').lower()=='lax'
        call('/api/auth/me',status=401)
        print('PASS: private session cookie has Secure, HttpOnly and SameSite; cookie jar withheld it over HTTP')
        return
    assert js('/api/auth/me')['username']==f['username']
    profiles=js('/api/profiles')['profiles'];profile=next(x for x in profiles if x['maxAge']>=18)
    js('/api/profiles/'+str(profile['id'])+'/activate',{'accountPassword':f['password']})
    if not a.recover:assert js('/api/admin/local-media/scan',{})['found']>=1
    items=js('/api/local-media',headers={'X-Profile-Id':str(profile['id'])})['items']
    item=next(x for x in items if 'Jobbi Pilot' in x['title'])
    path='/api/local-media/stream/'+str(item['id'])
    assert call(path,headers={'Range':'bytes=0-63'},status=206)==media.read_bytes()[:64]
    assert hashlib.sha256(call(path)).hexdigest()==f['sha256']
    js('/api/auth/logout',{})
    call('/api/auth/me',status=401)
    call(path,status=401)
    print('PASS: '+('restored ' if a.recover else '')+'account, profile, catalog, byte-range and complete generated-video transfer, logout and unauthorized denial')
if __name__=='__main__':main()
