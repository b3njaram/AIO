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
