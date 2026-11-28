from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from private_origins import prepare, rollback

class OriginTests(unittest.TestCase):
    def test_media_roundtrip(self):
        with TemporaryDirectory() as tmp:
            i=Path(tmp);(i/'deployment').mkdir()
            (i/'.env').write_text('X=1\n');(i/'dashboard.json').write_text('{}')
            p=i/'deployment/pilot-media.json';p.write_bytes(b'original-secret')
            prepare(i,{}, {},media=b'changed-secret')
            self.assertEqual(p.read_bytes(),b'changed-secret')
            self.assertEqual(p.stat().st_mode&0o777,0o600)
            rollback(i)
            self.assertEqual(p.read_bytes(),b'original-secret')
    def test_roundtrip_and_conflicting_edits(self):
        with TemporaryDirectory() as tmp:
            i=Path(tmp)
            original=b'TASK_URL=http://local/\nSECRET=private\n'
            (i/'.env').write_bytes(original)
            (i/'dashboard.json').write_bytes(b'{}\n')
            prepare(i,{'apps':[]},{'TASK_URL':'https://private/'})
            updated=(i/'.env').read_bytes()
            self.assertIn(b'SECRET=private\n',updated)
            with self.assertRaises(FileExistsError):
                prepare(i,{}, {})
            (i/'.env').write_bytes(updated+b'NEW=value\n')
            with self.assertRaises(ValueError):
                rollback(i)
            (i/'.env').write_bytes(updated)
            rollback(i)
            self.assertEqual((i/'.env').read_bytes(),original)
            self.assertEqual((i/'dashboard.json').read_bytes(),b'{}\n')
