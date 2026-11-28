import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('laptop_iso',Path(__file__).with_name('make-laptop-iso.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_interactive_no_disk_selection_or_credentials(self):
        cfg=m.config('a'*40)['autoinstall']
        self.assertEqual(cfg['interactive-sections'],['storage','identity'])
        self.assertNotIn('storage',cfg);self.assertNotIn('identity',cfg)
        self.assertFalse(cfg['ssh']['install-server'])
        self.assertIn('a'*40,str(cfg))
        self.assertNotIn('password_hash',str(cfg))
    def test_bad_revision(self):
        with self.assertRaises(ValueError):m.config('main')
