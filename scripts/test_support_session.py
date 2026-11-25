import importlib.util,unittest,tempfile,threading,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import Mock
spec=importlib.util.spec_from_file_location('support_session',Path(__file__).with_name('support-session.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_tailnet_identity(self):
        status={'BackendState':'Running','Self':{'Online':True,'DNSName':'home.demo.ts.net.','TailscaleIPs':['100.100.1.2']}}
        self.assertEqual(m.identity(status),('home.demo.ts.net','100.100.1.2'))
        status['Self']['TailscaleIPs']=['192.168.0.2']
        with self.assertRaises(ValueError):m.identity(status)
    def test_read_only_expiry_and_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            read=Mock(return_value={'schema':1,'kind':'jobbi-health-share','appliance_id':'HOME1'})
            event=Mock();s=m.Session(Path(tmp),'HOME1',5,read,event)
            server=m.Server('127.0.0.1',0,'127.0.0.1',s)
            t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
            def req(auth=None,host=None,data=None):
                h={}
                if auth:h['Authorization']='Bearer '+auth
                if host:h['Host']=host
                q=urllib.request.Request('http://'+server.host_header+'/api/report',headers=h,data=data)
                try:
                    with urllib.request.urlopen(q,timeout=5) as r:return r.status
                except urllib.error.HTTPError as e:return e.code
            try:
                self.assertEqual(req(),401);self.assertEqual(req('wrong'),401)
                self.assertEqual(req(s.token,'evil.example'),403)
                self.assertEqual(req(s.token,data=b'{}'),405);read.assert_not_called()
                self.assertEqual(req(s.token),200);event.assert_called_once_with(Path(tmp),'report_viewed')
                s.deadline=0;self.assertEqual(req(s.token),410);read.assert_called_once()
            finally:server.shutdown();server.server_close();t.join()
if __name__=='__main__':unittest.main()
