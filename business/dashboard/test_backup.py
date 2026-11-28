import hashlib,os,unittest,tempfile,sqlite3,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('backup_records',Path(__file__).with_name('backup-records.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BackupTests(unittest.TestCase):
    def test_online_ledger_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mount=Path('/dev/shm')
            if not mount.is_dir() or root.stat().st_dev==mount.stat().st_dev:
                self.skipTest('A second temporary filesystem is required')
            with tempfile.TemporaryDirectory(dir=mount) as dest:
                src=root/'cash.sqlite3'
                with sqlite3.connect(src) as writer:
                    writer.execute('PRAGMA journal_mode=WAL')
                    writer.execute('CREATE TABLE payments(amount INTEGER)')
                    writer.execute('INSERT INTO payments VALUES (125)')
                    writer.commit()
                    src.chmod(0o600)
                    previous=os.umask(0o077)
                    try:
                        folder=m.backup(src,dest)
                    finally:
                        os.umask(previous)
                    writer.execute('DELETE FROM payments')
                recovered=m.restore(folder,root/'restored')
                with self.assertRaises(FileExistsError):m.restore(folder,root/'restored')
                (folder/'cash.sqlite3').write_bytes(b'damaged')
                with self.assertRaisesRegex(ValueError,'checksum mismatch'):m.restore(folder,root/'damaged')
                self.assertFalse((root/'damaged/cash.sqlite3').exists())
                self.assertEqual(recovered.stat().st_mode & 0o777,0o600)
                digest=hashlib.sha256(recovered.read_bytes()).hexdigest()
                self.assertEqual((folder/'SHA256SUMS').read_text(),digest+'  cash.sqlite3\n')
                with sqlite3.connect(recovered.as_uri()+'?mode=ro',uri=True) as reader:
                    self.assertEqual(reader.execute('SELECT amount FROM payments').fetchall(),[(125,)])

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
