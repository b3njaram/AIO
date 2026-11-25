import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('private_access',Path(__file__).with_name('private-access.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def setUp(self):
        self.env={'BIND_IP':'127.0.0.1','DASH_PORT':'18080','VAULT_PORT':'18087','TASK_PORT':'18088'}
        self.config={'apps':[{'id':'passwords'},{'id':'tasks'}]}
    def test_routes(self):
        p=m.routes(self.env,self.config,'customer.example.ts.net.',19443)
        self.assertEqual(p['dashboard']['url'],'https://customer.example.ts.net:19443')
        self.assertEqual(p['passwords']['target'],'http://127.0.0.1:18087')
        self.assertNotIn('prowlarr',p)
        self.assertTrue(all('funnel' not in x for x in m.commands(p)['enable']))
    def test_refusals(self):
        for host in ('example.com','x.ts.net/abc','x.ts.net;touch'):
            with self.assertRaises(ValueError):m.routes(self.env,self.config,host,19443)
        with self.assertRaises(ValueError):m.routes({**self.env,'BIND_IP':'0.0.0.0'},self.config,'customer.example.ts.net',19443)
        with self.assertRaises(ValueError):m.existing_conflicts({'TCP':{'443':{}}},{19443})
    def test_verify(self):
        host='customer.example.ts.net';p=m.routes(self.env,self.config,host,19443)
        status={'TCP':{str(r['port']):{'HTTPS':True} for r in p.values()},'Web':{host+':'+str(r['port']):{'Handlers':{'/':{'Proxy':r['target']}}} for r in p.values()}}
        self.assertTrue(m.verify_config(status,p,host))
        with self.assertRaises(ValueError):m.verify_config({**status,'AllowFunnel':{host+':19443':True}},p,host)
        with self.assertRaises(ValueError):m.verify_config({'TCP':status['TCP'],'Web':{}},p,host)
if __name__=='__main__':unittest.main()
