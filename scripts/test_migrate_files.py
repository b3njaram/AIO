import importlib.util,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('migration',Path(__file__).with_name('migrate-files.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);s=p/'source';s.mkdir();d=p/'dest';d.mkdir()
            (s/'track.flac').write_bytes(b'fixture');(s/'other.txt').write_text('skip')
            rows,skipped=m.plan(s,'music');self.assertEqual((len(rows),skipped),(1,1))
            result=m.copy(s,d,rows);self.assertEqual(result[0]['size'],7);self.assertEqual((d/'track.flac').read_bytes(),b'fixture')
            with self.assertRaises(FileExistsError):m.copy(s,d,rows)
            (s/'link.flac').symlink_to(s/'track.flac')
            with self.assertRaises(ValueError):m.plan(s,'music')
if __name__=='__main__':unittest.main()
