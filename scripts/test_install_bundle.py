import tempfile,json,unittest
from pathlib import Path
from offline_kit import HELPER,digest
from install_bundle import check
class Tests(unittest.TestCase):
    def test_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);k=p/'kit';k.mkdir();r={'aio_commit':'a'*40,'source_pins':{},'customer_patch_version':5}
            for name in ('aio-source.tar.gz','helper.tar.gz'):(k/name).write_bytes(b'fixture')
            (k/'kit.json').write_text(json.dumps({'schema':1,'release':r['aio_commit'],'source_pins':{},'helper_reference':HELPER,'helper_id':'sha256:'+'b'*64,'files':{x.name:digest(x) for x in k.iterdir()}}))
            inv={'schema':1,'project':'jobbi-reference','services':{'dashboard':{'id':'sha256:'+'c'*64,'reference':'jobbi-reference-dashboard','repo_digests':[]}}}
            (p/'inventory.json').write_text(json.dumps(inv));(p/'images.tar.gz').write_bytes(b'fixture')
            (p/'bundle.json').write_text(json.dumps({'schema':1,'release':r,'apps':['monitor'],'files':{n:digest(p/n) for n in ('images.tar.gz','inventory.json')}}))
            self.assertEqual(check(p,r,{'monitor'})[0],inv)
            with self.assertRaises(ValueError):check(p,r,{'music'})
            (p/'images.tar.gz').write_bytes(b'changed')
            with self.assertRaises(ValueError):check(p,r,{'monitor'})
if __name__=='__main__':unittest.main()
