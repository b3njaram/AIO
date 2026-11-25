import importlib.util,unittest,tempfile,threading,urllib.request,urllib.error,ssl,subprocess,os,http.client,shutil
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
    @unittest.skipUnless(shutil.which('openssl'),'OpenSSL test certificate generator required')
    def test_tls_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            i=Path(tmp);key=i/'test.key';cert=i/'test.crt';host='home.demo.ts.net'
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','2','-subj','/CN='+host,'-addext','subjectAltName=DNS:'+host],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            key.chmod(0o600)
            ctx=m.tls_context(cert,key,host)
            with self.assertRaises(ValueError):m.tls_context(cert,key,'other.demo.ts.net')
            s=m.Session(i,'HOME1',5,Mock(return_value={'schema':1}),Mock());server=m.Server('127.0.0.1',0,host,s,ctx)
            t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
            import socket
            try:
                trust=ssl.create_default_context(cafile=str(cert))
                with trust.wrap_socket(socket.create_connection(('127.0.0.1',server.server_port),5),server_hostname=host) as sock:
                    sock.sendall(('GET /api/report HTTP/1.1\r\nHost: '+server.host_header+'\r\nAuthorization: Bearer '+s.token+'\r\nConnection: close\r\n\r\n').encode())
                    response=http.client.HTTPResponse(sock);response.begin()
                    self.assertEqual(response.status,200);self.assertEqual(response.read(),b'{"schema": 1}')
                with self.assertRaises(ssl.SSLCertVerificationError):
                    with trust.wrap_socket(socket.create_connection(('127.0.0.1',server.server_port),5),server_hostname='wrong.demo.ts.net'):pass
            finally:server.shutdown();server.server_close();t.join()
if __name__=='__main__':unittest.main()

