#!/usr/bin/env python3
"""Disposable CI only. Authenticate and verify persisted DNS, monitor and vault data."""
import base64
import http.cookiejar
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('account_setup',Path(__file__).with_name('setup-accounts.py'))
account_setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(account_setup)


def request(url,data=None,token=None,form=False,opener=None):
    headers={'Accept':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    if data is not None:
        headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
        data=(urllib.parse.urlencode(data) if form else json.dumps(data)).encode()
    q=urllib.request.Request(url,data=data,headers=headers)
    try:
        response=(opener or urllib.request.build_opener()).open(q,timeout=15)
    except urllib.error.HTTPError as error:
        return error.code,None
    with response:
        body=response.read()
        return response.status,json.loads(body) if body and 'application/json' in response.headers.get('Content-Type','') else None


def wait(fn,label='service'):
    for _ in range(90):
        try:
            if fn():return
        except (OSError,ValueError):pass
        time.sleep(2)
    raise RuntimeError(label+' readiness deadline exceeded')


def vault(instance,env,fixture,recover):
    base='http://127.0.0.1:'+env['VAULT_PORT']
    wait(lambda:request(base+'/alive')[0]==200)
    email='owner@example.invalid'
    def registration(email):
        return {'email':email,'name':'Synthetic owner','masterPasswordHash':fixture['password'],'key':fixture['cipher']}
    verify=base+'/identity/accounts/register/send-verification-email'
    assert request(verify,{'email':'other@example.invalid'})[0]==400
    if not recover:
        account_setup.invite_vault(instance,email)
        code,verification=request(verify,{'email':email})
        assert code==200 and isinstance(verification,str)
        payload={**registration(email),'emailVerificationToken':verification,'kdf':0,'kdfIterations':600000}
        code,_=request(base+'/identity/accounts/register/finish',payload)
        assert code==200,'Registration HTTP '+str(code)
    code,login=request(base+'/identity/connect/token',{'grant_type':'password','client_id':'web','scope':'api offline_access','username':email,'password':fixture['password'],'deviceIdentifier':fixture['device'],'deviceName':'Disposable CI','deviceType':'9'},form=True)
    assert code==200,'Vault login HTTP '+str(code)
    token=login['access_token']
    if not recover:
        code,row=request(base+'/api/folders',{'name':fixture['cipher']},token)
        assert code==200
        fixture['folder']=row['id']
    path=base+'/api/folders/'+fixture['folder']
    assert request(path)[0]==401
    code,item=request(path,token=token)
    assert code==200 and item['name']==fixture['cipher']
    print('PASS Vaultwarden owner login, closed signup, private encrypted folder bytes')


def monitor(instance,env,fixture,recover):
    import socketio
    # Validate the installed package versions and retained embedded browser on
    # both source and exact-image recovery, not merely a rebuilt test image.
    ctl=['bash',str(Path(__file__).with_name('ctl.sh')),str(instance),'exec','-T','uptime-kuma']
    for pkg in ('chromium','chromium-common'):
        version=subprocess.check_output([*ctl,'dpkg-query','-W','-f=${Version}',pkg],text=True).strip()
        assert version=='156.0.8078.108-1~deb12u1', 'Unexpected embedded browser package version'
    dom=subprocess.check_output([*ctl,'chromium','--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--dump-dom','data:text/html,<p>jobbi-browser-fixture</p>'],text=True,timeout=60,stderr=subprocess.DEVNULL)
    assert 'jobbi-browser-fixture' in dom
    print('PASS patched Chromium package and embedded browser functionality')
    base='http://127.0.0.1:'+env['MONITOR_PORT']
    if not recover:
        wait(lambda:request(base+'/')[0]==200,'Kuma UI')
        account_setup.create(instance,'monitor','pilot','pilot@example.invalid',fixture['password'])
    client=socketio.Client(reconnection=False)
    def connect():
        try:client.connect(base,transports=['polling']);return True
        except socketio.exceptions.ConnectionError:return False
    wait(connect)
    try:
        assert client.call('getMonitorList')['ok'] is False
        assert client.call('login',{'username':'pilot','password':fixture['password']})['ok']
        if not recover:
            row=client.call('add',{'name':'Local dashboard','type':'http','url':'http://dashboard:8080/healthz','interval':60,'accepted_statuscodes':['200-299'],'notificationIDList':{},'active':False,'conditions':[],'kafkaProducerBrokers':[],'kafkaProducerSaslOptions':{},'rabbitmqNodes':[]})
            assert row['ok'],row.get('msg')
            fixture['monitor']=row['monitorID']
        row=client.call('getMonitor',fixture['monitor'])
        assert row['ok'] and row['monitor']['name']=='Local dashboard'
    finally:client.disconnect()
    import importlib.util
    spec=importlib.util.spec_from_file_location('configure_monitors',Path(__file__).with_name('configure-monitors.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    e,desired=module.targets(instance)
    first=module.configure(e,desired,'pilot',fixture['password'],True)
    assert set(first['created'])==(set() if recover else set(desired)-{'dashboard'}),first
    assert module.configure(e,desired,'pilot',fixture['password'],True)['created']==[]
    print('PASS Uptime Kuma owner login, anonymous denial and saved monitor')


def dns(instance,env,recover):
    base='http://127.0.0.1:'+env['DNS_WEB_PORT']+'/api'
    def api_ready():
        try:
            status,_=request(base+'/auth')
            if status in (200,401):return True
            print('Pi-hole authentication readiness HTTP',status,flush=True)
        except OSError as exc:
            print('Pi-hole connection readiness',type(exc).__name__,flush=True)
        return False
    wait(api_ready,'Pi-hole API')
    status,auth=request(base+'/auth',{'password':env['DNS_PASSWORD']})
    assert status==200 and auth['session']['valid'],'Pi-hole login HTTP '+str(status)
    name='jobbi-synthetic.example.test'
    if not recover:
        subprocess.run(['bash',str(Path(__file__).with_name('ctl.sh')),str(instance),'exec','-T','pihole','pihole','deny',name],check=True)
    lookup=['dig','+short','+time=2','+tries=1','@127.0.0.1','-p',env['DNS_LISTEN_PORT'],name,'A']
    wait(lambda:subprocess.check_output(lookup,text=True).strip()=='0.0.0.0','Pi-hole blocked DNS response')
    assert subprocess.check_output([*lookup,'+tcp'],text=True).strip()=='0.0.0.0'
    print('PASS Pi-hole authenticated administration and persisted UDP/TCP blocking rule')


def main():
    instance=Path(sys.argv[1]).resolve()
    if os.environ.get('GITHUB_ACTIONS')!='true' or instance.parent!=Path('/tmp/jobbi-infra') or instance.name not in ('source','recovered'):
        raise ValueError('Disposable infrastructure CI only')
    env=dict(line.split('=',1) for line in (instance/'.env').read_text().splitlines() if '=' in line)
    assert env['INSTANCE_DIR']==str(instance) and env['BIND_IP']=='127.0.0.1'
    recover=instance.name=='recovered'
    path=instance.parent/'fixture.json'
    if recover:fixture=json.loads(path.read_text())
    else:
        encoded=lambda n:base64.b64encode(secrets.token_bytes(n)).decode()
        fixture={'password':secrets.token_urlsafe(32),'device':str(uuid.uuid4()),'cipher':'2.'+'|'.join(encoded(n) for n in (16,32,32))}
    vault(instance,env,fixture,recover)
    monitor(instance,env,fixture,recover)
    dns(instance,env,recover)
    if not recover:
        with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as out:json.dump(fixture,out)


if __name__=='__main__':main()
