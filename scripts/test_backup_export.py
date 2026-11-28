import hashlib,importlib.util,os,shutil,subprocess,tarfile,tempfile,unittest
from pathlib import Path
from backup_mount import mount_identity
spec=importlib.util.spec_from_file_location('backup_export',Path(__file__).with_name('backup-export.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
@unittest.skipUnless(shutil.which('age') and shutil.which('age-keygen'),'age required for encrypted integration test')
class Tests(unittest.TestCase):
    def test_roundtrip_and_wrong_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);b=p/'backup';b.mkdir();src=p/'fixture';src.mkdir()
            for name,body in {'.env':'COMPOSE_PROJECT_NAME=jobbi-demo\nINSTANCE_DIR=/tmp/demo\n','release.json':'{"aio_commit":"fixture"}','dashboard.json':'{"apps":[]}'}.items():(src/name).write_text(body)
            a=b/'instance.tar.gz'
            with tarfile.open(a,'w:gz') as tar:
                for x in src.iterdir():tar.add(x,arcname=x.name)
            (b/'SHA256SUMS').write_text(hashlib.sha256(a.read_bytes()).hexdigest()+'  instance.tar.gz\n')
            key=p/'key';subprocess.run(['age-keygen','-o',str(key)],check=True,capture_output=True);key.chmod(0o600)
            recipient=subprocess.check_output(['age-keygen','-y',str(key)],text=True).strip()
            encrypted=p/'backup.age';m.export(b,encrypted,recipient)
            with self.assertRaises(ValueError):m.export(b,encrypted,recipient)
            wrong=p/'wrong';subprocess.run(['age-keygen','-o',str(wrong)],check=True,capture_output=True);wrong.chmod(0o600)
            with self.assertRaises((ValueError,tarfile.TarError)):m.recover(encrypted,p/'bad',wrong,'jobbi-demo',mount_identity(p))
            self.assertFalse((p/'bad').exists())
            m.recover(encrypted,p/'restored',key,'jobbi-demo',mount_identity(p))
            self.assertEqual((p/'restored/instance.tar.gz').read_bytes(),a.read_bytes())
            with self.assertRaises(ValueError):m.recover(encrypted,p/'wrong-project',key,'jobbi-other',mount_identity(p))
            self.assertFalse((p/'wrong-project').exists())
if __name__=='__main__':unittest.main()
