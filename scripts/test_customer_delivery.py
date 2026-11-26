import unittest,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('delivery',Path(__file__).with_name('customer-delivery.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_guide(self):
        cfg={'apps':[{'id':'music','url':'https://home.demo.ts.net:19444','secret':'not printed'},{'id':'files'}]}
        for lang in ('en','es'):
            body=m.guide(cfg,{'aio_commit':'a'*40,'secret':'private'},lang)
            self.assertIn('https://home.demo.ts.net:19444',body);self.assertIn('Nextcloud',body);self.assertIn('- [ ]',body)
            self.assertNotIn('not printed',body);self.assertNotIn('secret',body)
        cfg['apps'][0]['url']='https://user:password@home.demo.ts.net'
        with self.assertRaises(ValueError):m.guide(cfg,{'aio_commit':'a'*40},'en')
if __name__=='__main__':unittest.main()
