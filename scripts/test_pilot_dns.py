import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('pilot_dns',Path(__file__).with_name('pilot-dns.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_isolated(self):
        p=m.config(Path('/srv/jobbi-data/laptop-test'),'fixture-password')['services']['pilot-pihole']
        self.assertEqual(p['environment']['FTLCONF_dhcp_active'],'false')
        self.assertTrue(all(x.startswith('127.0.0.1:') for x in p['ports']))
        self.assertIn('127.0.0.1:1053:53/udp',p['ports'])
        with self.assertRaises(ValueError):m.config(Path('/tmp'),'$fixture-password')

    def test_native_profile_preserves_existing_credentials_and_app(self):
        e={'COMPOSE_PROFILES':'music,monitor','DNS_WEB_PORT':'18089','DNS_PASSWORD':'old-generated','MUSIC_ADMIN':'owner','DASH_PORT':'18080'}
        cfg={'name':'test','apps':[{'id':'music'}]}
        new,proposed=m.native_config(e,cfg,'new-password-123',1053)
        self.assertEqual(new['COMPOSE_PROFILES'],'dns,monitor,music')
        self.assertEqual(new['DNS_LISTEN_PORT'],'1053')
        self.assertEqual(new['DNS_PASSWORD'],'new-password-123')
        self.assertEqual(new['MUSIC_ADMIN'],'owner')
        self.assertEqual(proposed['apps'][-1]['probe'],'http://pihole/admin/')
        self.assertEqual(cfg['apps'],[{'id':'music'}])
        with self.assertRaises(ValueError):m.native_config(new,proposed,'other-password',1054)
        with self.assertRaises(ValueError):m.native_config(e,cfg,'valid-password',18080)
        with self.assertRaises(ValueError):m.native_config(e,cfg,'unsafe # password',1053)
