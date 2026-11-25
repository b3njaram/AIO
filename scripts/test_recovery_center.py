import importlib.util,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('recovery_center',Path(__file__).with_name('recovery-center.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_retention_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);i=root/'home';i.mkdir();b=root/'backup';b.mkdir()
            dates=['20200104T000000Z','20200103T000000Z','20200102T000000Z','20200101T000000Z']
            rows=[b/('jobbi-home-'+x) for x in dates]
            for x in rows:x.mkdir()
            with patch.object(m,'candidates',return_value=rows),patch.object(m,'verified') as verify:
                result=m.retention(i,b,3,30)
                self.assertEqual(verify.call_count,3)
                self.assertEqual([x['decision'] for x in result],['keep']*3+['review_for_manual_retention'])
                self.assertTrue(all(x.is_dir() for x in rows))
                with self.assertRaises(ValueError):m.retention(i,b,2,30)
                (i/'.upgrade-hold.json').touch()
                with self.assertRaises(ValueError):m.retention(i,b,3,30)
    def test_refuses_unverified_recent(self):
        with tempfile.TemporaryDirectory() as tmp:
            i=Path(tmp)
            with patch.object(m,'candidates',return_value=[i/str(n) for n in range(4)]),patch.object(m,'verified',side_effect=ValueError('bad checksum')):
                with self.assertRaisesRegex(ValueError,'bad checksum'):m.retention(i,i,3,30)
if __name__=='__main__':unittest.main()
