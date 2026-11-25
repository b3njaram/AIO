import importlib.util,json,http.client,ssl,socket,subprocess,tempfile,threading,unittest,shutil
from pathlib import Path
from unittest.mock import patch
import server,customers
spec=importlib.util.spec_from_file_location('receiver',Path(__file__).with_name('health-receiver.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
@unittest.skipUnless(shutil.which('openssl'),'OpenSSL required')
class Tests(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(server,'HOME',Path(tmp)):
            i=Path(tmp);key=i/'fixture.key';cert=i/'fixture.crt';host='owner.demo.ts.net'
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','2','-subj','/CN='+host,'-addext','subjectAltName=DNS:'+host],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            key.chmod(0o600)
            server.save_order({'id':'ORDER','market':'US','total':'100'},True)
            with server.db() as db:
                customers.save(db,{'id':'HOME1','order_id':'ORDER','label':'Fixture'})
                customers.consent(db,{'id':'HOME1','allow':True,'confirmed':True})
                grant=customers.enable_reporting(db,{'id':'HOME1','confirmed':True})
            def report():return {'schema':1,'kind':'jobbi-health-share','appliance_id':'HOME1','at':customers.now().isoformat(),'release':'a'*40,'free_percent':60,'temperature_c':40,'alerts':0,'backup':'verified','raid':'healthy','updates':'current'}
            r=m.Receiver('127.0.0.1',0,host,m.support.tls_context(cert,key,host))
            thread=threading.Thread(target=r.serve_forever,daemon=True);thread.start();trust=ssl.create_default_context(cafile=str(cert))
            def req(token=None,data=None,method='POST',path='/v1/health',origin=None,hostname=None):
                body=json.dumps(data).encode() if data is not None else b''
                headers={'Host':hostname or r.host_header,'Content-Type':'application/json','Content-Length':str(len(body)),'Connection':'close'}
                if token:headers['Authorization']='Bearer '+token
                if origin:headers['Origin']=origin
                with trust.wrap_socket(socket.create_connection(('127.0.0.1',r.server_port),5),server_hostname=host) as sock:
                    sock.sendall((method+' '+path+' HTTP/1.1\r\n'+''.join(k+': '+v+'\r\n' for k,v in headers.items())+'\r\n').encode()+body)
                    response=http.client.HTTPResponse(sock);response.begin();return response.status,response.read()
            try:
                token=grant['token'];payload=report()
                self.assertEqual(req(data=payload)[0],401)
                self.assertEqual(req('x'*43,payload)[0],403)
                self.assertEqual(req(token,payload,origin='https://example.com')[0],403)
                self.assertEqual(req(token,payload,hostname='wrong')[0],403)
                self.assertEqual(req(token,{**payload,'appliance_id':'OTHER'})[0],403)
                self.assertEqual(req(token,payload,path='/api/orders')[0],403)
                self.assertEqual(req(token,method='GET',path='/api/orders'),(404,b'{"ok":false}'))
                self.assertEqual(req(token,payload)[0],200)
                self.assertEqual(req(token,payload)[0],403)
                with server.db() as db:
                    self.assertEqual(customers.rows(db)[0]['report'],payload)
                    customers.consent(db,{'id':'HOME1','allow':False,'confirmed':True})
                self.assertEqual(req(token,report())[0],403)
                with server.db() as db:self.assertIsNone(customers.rows(db)[0]['report'])
            finally:r.shutdown();r.server_close();thread.join()
if __name__=='__main__':unittest.main()
