import unittest,tempfile,sqlite3,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('backup_records',Path(__file__).with_name('backup-records.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BackupTests(unittest.TestCase):
    def test_refuses_same_filesystem(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'test.sqlite3'
            with sqlite3.connect(src) as db:db.execute('CREATE TABLE demo(x)')
            src.chmod(0o600)
            with self.assertRaisesRegex(ValueError,'separate mounted'):m.backup(src,root)
    def test_refuses_public_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'test.sqlite3'
            src.write_text('x');src.chmod(0o644)
            with self.assertRaisesRegex(ValueError,'not private'):m.backup(src,root)
if __name__=='__main__':unittest.main()
