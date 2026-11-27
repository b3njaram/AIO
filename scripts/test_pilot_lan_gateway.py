import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('gateway',Path(__file__).with_name('pilot-lan-gateway.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_scope(self):
        c=m.config('192.168.1.166','192.168.1.20')
        self.assertEqual(c.count('deny all;'),9)
        self.assertEqual(c.count('allow 192.168.1.20;'),9)
        self.assertNotIn('18084',c)
        self.assertNotIn('0.0.0.0',c)
        self.assertIn('location ~ ^/admin',c)
    def test_optional_routes_are_explicit(self):
        c=m.config('192.168.1.166','192.168.1.20',{'dns','invidious'})
        self.assertEqual(c.count('deny all;'),11)
        self.assertIn('listen 192.168.1.166:18089 ssl;',c)
        self.assertIn('listen 192.168.1.166:18091 ssl;',c)
        self.assertNotIn('1053',c)
        with self.assertRaises(ValueError):m.config('192.168.1.166','192.168.1.20',{'unknown'})
    def test_reject_nonprivate(self):
        with self.assertRaises(ValueError):m.config('8.8.8.8','192.168.1.20')
        with self.assertRaises(ValueError):m.config('192.168.1.20','192.168.1.20')
