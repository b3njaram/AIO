import importlib.util,tempfile,threading,unittest,urllib.request,urllib.error,json
from pathlib import Path
from unittest.mock import Mock
spec=importlib.util.spec_from_file_location('manage_web',Path(__file__).with_name('manage-web.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter=Mock();adapter.status.return_value=[{'app':'music','state':'running','health':'not_checked'}];adapter.restart.return_value={'applied':True}
            s=m.Session(Path(tmp),5,adapter);server=m.Server(0,s);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def req(path,data=None,auth=True,origin=None,host=None):
                h={}
                if auth:h['Authorization']='Bearer '+s.token
                if host:h['Host']=host
                if data is not None:h.update({'Content-Type':'application/json','Origin':origin or server.origin,'X-Jobbi-Setup':'1'})
                q=urllib.request.Request(server.origin+path,headers=h,data=None if data is None else json.dumps(data).encode())
                try:
                    with urllib.request.urlopen(q,timeout=5) as r:return r.status
                except urllib.error.HTTPError as e:return e.code
            try:
                self.assertEqual(req('/api/status',auth=False),401)
                self.assertEqual(req('/api/status',host='evil.test'),403)
                self.assertEqual(req('/api/restart',{'app':'music','confirm':True},origin='https://evil.test'),403)
                self.assertEqual(req('/api/restart',{'app':'music','confirm':False}),400)
                adapter.restart.assert_not_called()
                self.assertEqual(req('/api/restart',{'app':'music','confirm':True}),200)
                adapter.restart.assert_called_once_with(Path(tmp),'music',True)
                self.assertEqual(req('/api/finish',{}),200)
                self.assertEqual(req('/api/status'),410)
            finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
