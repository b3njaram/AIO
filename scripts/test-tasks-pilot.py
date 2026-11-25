#!/usr/bin/env python3
"""Disposable full-stack CI only: check closed registration and actual task persistence."""
import json,os,secrets,subprocess,urllib.request,urllib.error,time
from pathlib import Path
import pilot_fixture as fixture
ROOT=Path(__file__).resolve().parents[1]
def main():
    i=fixture.location()
    recover=i.name=='recovered'
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    assert os.getenv('GITHUB_ACTIONS')=='true' and env['INSTANCE_DIR']==str(i) and env['COMPOSE_PROJECT_NAME']=='jobbi-'+i.name and env['BIND_IP']=='127.0.0.1'
    base='http://127.0.0.1:'+env['TASK_PORT']+'/api/v1'
    user='pilot'+secrets.token_hex(4);pw=secrets.token_urlsafe(24);email=user+'@example.invalid'
    def request(path,method='GET',data=None,token=None):
        h={'Accept':'application/json'}
        if token:h['Authorization']='Bearer '+token
        b=None
        if data is not None:h['Content-Type']='application/json';b=json.dumps(data).encode()
        try:r=urllib.request.urlopen(urllib.request.Request(base+path,data=b,headers=h,method=method),timeout=15)
        except urllib.error.HTTPError as e:return e.code,{}
        with r:return r.status,json.loads(r.read())
    last_status='connection unavailable'
    for n in range(90):
        try:
            code,info=request('/info')
            last_status=str(code)
            if code==200:break
        except (OSError,ValueError):pass
        time.sleep(2)
    else:raise AssertionError('Vikunja API unavailable after 180s; last HTTP status: '+last_status)
    assert info.get('auth',{}).get('local',{}).get('registration_enabled') is False, 'Registration not closed or unknown API schema'
    code,_=request('/register','POST',{'username':user,'password':pw,'email':email})
    assert code in (400,403,404,405),f'Registration unexpectedly returned {code}'
    if recover:
        user,pw,task=fixture.load('tasks')
    else:
        subprocess.run(['bash',str(ROOT/'scripts/ctl.sh'),str(i),'exec','-T','vikunja','/app/vikunja/vikunja','user','create','--username',user,'--email',email,'--password',pw],check=True,stdout=subprocess.DEVNULL)
    code,login=request('/login','POST',{'username':user,'password':pw});assert code==200 and login.get('token')
    token=login['token']
    if not recover:
        code,project=request('/projects','PUT',{'title':'Jobbi pilot project'},token);assert code in (200,201) and project.get('id')
        code,task=request('/projects/'+str(project['id'])+'/tasks','PUT',{'title':'Jobbi synthetic task'},token);assert code in (200,201) and task.get('id')
    code,read=request('/tasks/'+str(task['id']),token=token);assert code==200 and read.get('title')=='Jobbi synthetic task'
    code,_=request('/tasks/'+str(task['id']));assert code==401
    print('PASS: closed registration, local user creation, login, project/task creation and unauthorized denial')
    if i.name=='source':fixture.save('tasks',[user,pw,task])
    if i.name!='full':return
    code,music=0,None
    with urllib.request.urlopen('http://127.0.0.1:'+env['MUSIC_PORT']+'/api/android/latest',timeout=10) as r:music=json.load(r)
    assert music.get('available') is False and 'compatible client' in music.get('reason','')
    print('PASS: commercial Android release feed disabled')
if __name__=='__main__':main()
