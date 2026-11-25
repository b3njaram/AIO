import importlib.util, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('setup_customer',Path(__file__).with_name('setup-customer.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class SetupTests(unittest.TestCase):
    def test_reject_same_filesystem(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);(d/'data').mkdir();(d/'backup').mkdir()
            a=SimpleNamespace(name='home',data_root=d/'data',backup_root=d/'backup',apps='monitor',quote=None,base_port=18080,tz='Etc/UTC',minimum_free_gib=1,minimum_docker_free_gib=1)
            with self.assertRaisesRegex(ValueError,'separate mounted'):m.plan(a)
            a.apps='dns'
            with self.assertRaisesRegex(ValueError,'Pi-hole'):m.plan(a)
    def test_invalid_name(self):
        a=SimpleNamespace(name='../bad')
        with self.assertRaisesRegex(ValueError,'Invalid customer name'):m.plan(a)
if __name__=='__main__':unittest.main()
