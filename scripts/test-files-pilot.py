#!/usr/bin/env python3
"""CI-only Nextcloud local setup, authenticated WebDAV and post-restart persistence."""
import base64,os,secrets,subprocess,time,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    instance=Path('/tmp/jobbi-full/full')
    env=dict(x.split('=',1) for x in (instance/'.env').read_text().splitlines() if '=' in x)
    assert os.getenv('GITHUB_ACTIONS')=='true' and env['INSTANCE_DIR']==str(instance) and env['COMPOSE_PROJECT_NAME']=='jobbi-full' and env['BIND_IP']=='127.0.0.1'
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(instance)]
    occ=ctl+['exec','-T','-u','www-data','nextcloud','php','occ']
    user='pilot'+secrets.token_hex(4);pw=secrets.token_urlsafe(24)
    # Only disposable CI credentials. Suppress command output to keep values out of logs.
    args=['maintenance:install','--database=pgsql','--database-host=nextcloud-db','--database-name=nextcloud','--database-user=nextcloud','--database-pass='+env['CLOUD_DB_PASSWORD'],'--admin-user='+user,'--admin-pass='+pw]
    for _ in range(30):
        r=subprocess.run(occ+args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120)
        if r.returncode==0:break
        time.sleep(3)
    else:raise RuntimeError('Nextcloud setup did not complete')
    subprocess.run(occ+['config:system:set','trusted_domains','1','--value=127.0.0.1'],check=True,stdout=subprocess.DEVNULL)
    base='http://127.0.0.1:'+env['CLOUD_PORT']
    url=base+'/remote.php/dav/files/'+user+'/jobbi-pilot.txt'
    auth='Basic '+base64.b64encode((user+':'+pw).encode()).decode()
    payload=b'Jobbi synthetic WebDAV fixture\n'
    def request(method,body=None,authorized=True):
        h={'Authorization':auth} if authorized else {}
        if body is not None:h['Content-Type']='application/octet-stream'
        q=urllib.request.Request(url,method=method,data=body,headers=h)
        try:r=urllib.request.urlopen(q,timeout=20)
        except urllib.error.HTTPError as e:return e.code,b''
        with r:return r.status,r.read()
    assert request('GET',authorized=False)[0]==401,'Anonymous access should be denied'
    assert request('PUT',payload)[0] in (201,204),'WebDAV upload failed'
    assert request('GET')==(200,payload),'WebDAV retrieval differs'
    subprocess.run(ctl+['restart','nextcloud'],check=True)
    for _ in range(30):
        try:
            if request('GET')==(200,payload):break
        except OSError:pass
        time.sleep(3)
    else:raise AssertionError('File not available after restart')
    assert request('DELETE')[0] in (200,204)
    assert request('GET')[0]==404
    print('PASS: Nextcloud admin setup, anonymous denial, WebDAV upload, byte-identical retrieval, restart persistence and deletion')
if __name__=='__main__':main()
