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
    def test_native_dns_admin_only(self):
        e={**self.env,'COMPOSE_PROFILES':'passwords,tasks,dns','DNS_WEB_PORT':'18089','DNS_LISTEN_PORT':'1053'}
        c={'apps':[*self.config['apps'],{'id':'dns'}]}
        p=m.routes(e,c,'customer.example.ts.net',19443)
        self.assertEqual(p['dns']['target'],'http://127.0.0.1:18089')
        self.assertNotIn('1053',str(p))
        self.assertEqual(p['dns']['port'],19452)
        with self.assertRaises(ValueError):m.routes({**e,'DNS_LISTEN_PORT':'53'},c,'customer.example.ts.net',19443)
        with self.assertRaises(ValueError):m.routes({**e,'DNS_LISTEN_PORT':'19452'},c,'customer.example.ts.net',19443)
        with self.assertRaises(ValueError):m.routes(e,{'apps':[{'id':'invidious'}]},'customer.example.ts.net',19443)
    def test_invidious_route(self):
        e={**self.env,'MUSIC_PORT':'18081'}
        c={'apps':[{'id':'music'}]}
        p=m.routes(e,c,'customer.example.ts.net',19443,True)
        self.assertEqual(p['invidious'],{'port':19453,'target':'http://127.0.0.1:18091','url':'https://customer.example.ts.net:19453'})
        self.assertNotIn('invidious-companion',p)
        self.assertNotIn('prowlarr',p)
    def test_refusals(self):
        for host in ('example.com','x.ts.net/abc','x.ts.net;touch'):
            with self.assertRaises(ValueError):m.routes(self.env,self.config,host,19443)
        with self.assertRaises(ValueError):m.routes({**self.env,'BIND_IP':'0.0.0.0'},self.config,'customer.example.ts.net',19443)
        with self.assertRaises(ValueError):m.existing_conflicts({'TCP':{'443':{}}},{19443})
    def test_verify(self):
        host='customer.example.ts.net';p=m.routes(self.env,self.config,host,19443)
        status={'TCP':{str(r['port']):{'HTTPS':True} for r in p.values()},'Web':{host+':'+str(r['port']):{'Handlers':{'/':{'Proxy':r['target']}}} for r in p.values()}}
        self.assertTrue(m.verify_config(status,p,host))
        for extra in ({'TCP':{**status['TCP'],'443':{'HTTPS':True}}},
                      {'Web':{**status['Web'],'other.ts.net:443':{}}},
                      {'Foreground':{'session':{}}}, {'Services':{'other':{}}},
                      {'UnknownConfig':True}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                m.verify_config({**status,**extra},p,host)
        with self.assertRaises(ValueError):m.verify_config({**status,'AllowFunnel':{host+':19443':True}},p,host)
        with self.assertRaises(ValueError):m.verify_config({'TCP':status['TCP'],'Web':{}},p,host)
if __name__=='__main__':unittest.main()
