import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('monitors',Path(__file__).with_name('configure-monitors.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_existing_urls(self):
        self.assertEqual(m.missing({'dashboard':'http://dashboard:8080/healthz','music':'http://jobbi-music:3131/api/status'},{'1':{'type':'http','url':'http://dashboard:8080/healthz','name':'Customer chosen name'}}),{'music':'http://jobbi-music:3131/api/status'})
    def test_login_timeout_retries_without_retrying_rejected_credentials(self):
        from types import SimpleNamespace
        class Timeout(Exception):pass
        class Connection(Exception):pass
        outcomes=[Timeout(),{'ok':True}]
        clients=[]
        class Client:
            def __init__(self,**kw):self.connected=False;clients.append(self)
            def connect(self,*a,**kw):self.connected=True
            def call(self,*a,**kw):
                result=outcomes.pop(0)
                if isinstance(result,Exception):raise result
                return result
            def disconnect(self):self.connected=False
        socket=SimpleNamespace(Client=Client,exceptions=SimpleNamespace(ConnectionError=Connection,TimeoutError=Timeout))
        self.assertIs(m.owner_session('3001','u','p',socket,sleep=lambda _:None),clients[-1])
        self.assertFalse(clients[0].connected)
        outcomes.extend([{'ok':False},{'ok':True}])
        with self.assertRaisesRegex(ValueError,'rejected'):m.owner_session('3001','u','p',socket,sleep=lambda _:None)
        self.assertEqual(len(outcomes),1)
        self.assertFalse(clients[-1].connected)
if __name__=='__main__':unittest.main()
