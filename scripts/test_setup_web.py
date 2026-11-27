import importlib.util,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import Mock
spec=importlib.util.spec_from_file_location('setup_web',Path(__file__).with_name('setup-web.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_local_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter=Mock();adapter.env_for.return_value={'COMPOSE_PROFILES':'music,passwords','MUSIC_ADMIN':'owner'}
            s=m.Session(Path(tmp),adapter=adapter);server=m.Server(0,s);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def req(path,data=None,auth=True,origin=None,host=None):
                headers={}
                if auth:headers['Authorization']='Bearer '+s.token
                if host:headers['Host']=host
                if data is not None:headers.update({'Origin':origin or server.origin,'Content-Type':'application/json','X-Jobbi-Setup':'1'})
                q=urllib.request.Request(server.origin+path,headers=headers,data=None if data is None else json.dumps(data).encode())
                try:
                    with urllib.request.urlopen(q,timeout=5) as r:return r.status,json.loads(r.read())
                except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
            payload={'app':'music','username':'owner','email':'owner@example.invalid','password':'fixture-password','confirm':'fixture-password'}
            try:
                self.assertEqual(req('/api/status',auth=False)[0],401)
                self.assertEqual(req('/api/status',host='evil.example')[0],403)
                self.assertEqual(req('/api/create',payload,origin='https://evil.example')[0],403)
                self.assertEqual(req('/api/create',{**payload,'app':'movies'})[0],400)
                self.assertEqual(req('/api/options',{'services':['dns'],'consent':True,'dns_password':'fixture-password'})[0],400)
                self.assertEqual(req('/api/tailnet',{'consent':True})[0],400)
                self.assertEqual(req('/api/options-recheck',{})[0],400)
                adapter.create.assert_not_called()
                self.assertEqual(req('/api/create',{**payload,'app':'all'})[0],200)
                adapter.create.assert_called_once_with(Path(tmp),'music','owner','owner@example.invalid','fixture-password')
                self.assertEqual(req('/api/create',payload)[0],400)
                self.assertEqual(req('/api/create',{**payload,'app':'passwords'})[0],400)
                self.assertEqual(req('/api/create',{**payload,'app':'passwords','password':'','confirm':''})[0],200)
                adapter.invite_vault.assert_called_once_with(Path(tmp),'owner@example.invalid')
                self.assertNotIn('fixture-password',json.dumps(req('/api/status')[1]))
                self.assertEqual(req('/api/finish',{})[0],200)
                self.assertEqual(req('/api/status')[0],410)
            finally:server.shutdown();server.server_close();thread.join()
    def test_rotate_only_expired_unfinished_paired_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter=Mock();adapter.env_for.return_value={'COMPOSE_PROFILES':'music','MUSIC_ADMIN':'owner'}
            s=m.Session(Path(tmp),adapter=adapter)
            self.assertEqual(m.expired_exit(s,True),0)
            s.lan={'address':'192.168.1.168'}
            self.assertEqual(m.expired_exit(s,False),0)
            self.assertEqual(m.expired_exit(s,True),75)
            (s.instance/'.pilot-lan-client.json').write_text('{}')
            self.assertEqual(m.expired_exit(s,True),0)
if __name__=='__main__':unittest.main()

