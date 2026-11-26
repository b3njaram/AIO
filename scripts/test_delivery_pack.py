import importlib.util,json,tempfile,unittest
from pathlib import Path
from offline_kit import digest
spec=importlib.util.spec_from_file_location('pack',Path(__file__).with_name('delivery-pack.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);i=p/'instance';i.mkdir();out=p/'pack'
            (i/'release.json').write_text(json.dumps({'aio_commit':'a'*40,'secret':'not exported'}))
            (i/'dashboard.json').write_text(json.dumps({'apps':[{'id':'music'}]}))
            (i/'.env').write_text('SECRET=not exported')
            m.build(i,out)
            record=json.loads((out/'acceptance-draft.json').read_text())
            self.assertFalse(record['approved']);self.assertEqual(record['apps'],{'music':'pending'})
            manifest=json.loads((out/'manifest.json').read_text())
            self.assertEqual(set(manifest['files']),{x.name for x in out.iterdir()}-{'manifest.json'})
            for name,sha in manifest['files'].items():
                self.assertEqual(sha,digest(out/name));self.assertNotIn('not exported',(out/name).read_text())
            with self.assertRaises(FileExistsError):m.build(i,out)
if __name__=='__main__':unittest.main()
