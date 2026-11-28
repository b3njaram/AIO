#!/usr/bin/env python3
"""CI-only Nextcloud local setup, authenticated WebDAV and post-restart persistence."""
import argparse,base64,os,secrets,subprocess,time,urllib.error,urllib.request
from pathlib import Path
import pilot_fixture as fixture
import importlib.util
spec=importlib.util.spec_from_file_location('account_setup',Path(__file__).with_name('setup-accounts.py'))
account_setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(account_setup)
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-original',action='store_true')
    args=parser.parse_args()
    instance=fixture.location()
    recover=instance.name in ('recovered','trial') or args.check_original
    env=dict(x.split('=',1) for x in (instance/'.env').read_text().splitlines() if '=' in x)
    assert os.getenv('GITHUB_ACTIONS')=='true' and env['INSTANCE_DIR']==str(instance) and env['COMPOSE_PROJECT_NAME']=='jobbi-'+instance.name and env['BIND_IP']=='127.0.0.1'
    ctl=['bash',str(ROOT/'scripts/ctl.sh'),str(instance)]
    occ=ctl+['exec','-T','-u','www-data','nextcloud','php','occ']
    user='pilot'+secrets.token_hex(4);pw=secrets.token_urlsafe(24)
    # Only disposable CI credentials. Suppress command output to keep values out of logs.
    if recover:
        user,pw=fixture.load('files')
    else:
        for _ in range(30):
            try:
                account_setup.create(instance,'files',user,'pilot@example.invalid',pw)
                break
            except (OSError,ValueError):time.sleep(3)
        else:raise RuntimeError('Nextcloud guided account setup did not complete')
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
    if recover:
        for _ in range(45):
            try:
                if request('GET')==(200,payload):break
            except OSError:pass
            time.sleep(2)
        else:raise AssertionError('Restored Nextcloud content unavailable')
        assert request('GET',authorized=False)[0]==401
        if instance.name=='trial':
            import json
            with urllib.request.urlopen(base+'/status.php',timeout=20) as response:
                status=json.load(response)
            assert status['versionstring'].startswith('33.0.11'),status
            assert status['installed'] and not status['maintenance'] and not status['needsDbUpgrade'],status
            print('PASS: Nextcloud 32 to 33 migration preserved account access and file contents')
        return
    # Exercise exact origin application and rollback before local WebDAV checks.
    import nextcloud_origin
    original=nextcloud_origin.read(instance)
    nextcloud_origin.prepare(instance,'https://fixture.example.ts.net:19448')
    nextcloud_origin.verify(instance,'https://fixture.example.ts.net:19448')
    nextcloud_origin.rollback(instance)
    assert nextcloud_origin.read(instance)==original
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
    if instance.name=='source':
        fixture.save('files',[user,pw]);return
    assert request('DELETE')[0] in (200,204)
    assert request('GET')[0]==404
    print('PASS: Nextcloud admin setup, anonymous denial, WebDAV upload, byte-identical retrieval, restart persistence and deletion')
if __name__=='__main__':main()
