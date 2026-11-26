import unittest,tempfile,json,tarfile,io,subprocess
from pathlib import Path
from offline_kit import HELPER,digest,verify,extract_source,archive,retain_sources,retained_archive,retained_manifest
class Tests(unittest.TestCase):
    def test_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);r={'aio_commit':'a'*40,'source_pins':{'movies':'b'*40}}
            for n in ('aio-source.tar.gz','helper.tar.gz','movies-source.tar.gz'):(p/n).write_bytes(b'fixture')
            m={'schema':1,'release':r['aio_commit'],'source_pins':r['source_pins'],'helper_id':'sha256:'+'c'*64,'helper_reference':HELPER,'files':{x.name:digest(x) for x in p.iterdir()}}
            (p/'kit.json').write_text(json.dumps(m))
            self.assertEqual(verify(p,r),m)
            with self.assertRaises(ValueError):verify(p,{**r,'aio_commit':'d'*40})
            (p/'helper.tar.gz').write_bytes(b'tampered')
            with self.assertRaises(ValueError):verify(p,r)
    def test_recovered_sources_can_be_exported_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            repo=root/'repo'
            subprocess.run(['git','init','-q',str(repo)],check=True)
            (repo/'original').write_bytes(b'original source')
            subprocess.run(['git','-C',str(repo),'add','original'],check=True)
            subprocess.run(['git','-C',str(repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
            pin=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
            kit=root/'kit';kit.mkdir()
            source=kit/'movies-source.tar.gz'
            archive(repo,pin,source)
            instance=root/'instance';instance.mkdir()
            release={'aio_commit':'a'*40,'source_pins':{'movies':pin}}
            m={'schema':1,'release':release['aio_commit'],'source_pins':release['source_pins'],'helper_id':'sha256:'+'c'*64,'helper_reference':HELPER,'files':{source.name:digest(source)}}
            retain_sources(instance,kit,m)
            source.unlink()
            cached=retained_manifest(instance,release)
            retained=retained_archive(instance,'movies',cached)
            self.assertEqual(digest(retained),m['files'][source.name])
            with self.assertRaises(ValueError):
                retained_archive(instance,'movies',{**cached,'source_pins':{'movies':'f'*40}})
            retained.write_bytes(b'damaged')
            with self.assertRaises(ValueError):retained_archive(instance,'movies',cached)

    def test_source_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);dest=p/'dest';dest.mkdir();a=p/'source.tar.gz'
            with tarfile.open(a,'w:gz') as t:
                m=tarfile.TarInfo('test.txt');m.size=3;t.addfile(m,io.BytesIO(b'abc'))
            extract_source(a,dest);self.assertEqual((dest/'test.txt').read_bytes(),b'abc')
            with tarfile.open(a,'w:gz') as t:
                m=tarfile.TarInfo('../escape');m.size=3;t.addfile(m,io.BytesIO(b'abc'))
            with self.assertRaises(ValueError):extract_source(a,dest)
            self.assertFalse((p/'escape').exists())
if __name__=='__main__':unittest.main()
