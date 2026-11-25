import importlib.util,unittest
from pathlib import Path
from types import SimpleNamespace
def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class Tests(unittest.TestCase):
    def test_seed(self):
        m=load('make-install-usb')
        a=SimpleNamespace(name='home',operator='jobbi',commit='a'*40,data_uuid='abcd-1234',backup_uuid='abcd-5678',apps='music,monitor',ssh_key='ssh-ed25519 AAAA')
        c=m.config(a,'$6$fixture')['autoinstall']
        self.assertEqual(c['interactive-sections'],['storage']);self.assertNotIn('storage',c)
        self.assertFalse(c['ssh']['allow-pw'])
        files={x['path']:x['content'] for x in c['user-data']['write_files']}
        self.assertIn('/etc/jobbi/install.json',files)
        self.assertIn('srv-jobbi\\x2ddata.mount',files['/etc/systemd/system/jobbi-first-boot.service'])
        a.backup_uuid=a.data_uuid
        with self.assertRaises(ValueError):m.config(a,'$6$fixture')
    def test_mount_guard(self):
        m=load('boot-guard');s=m.unit([('/srv/data','abcd-1234'),('/','abcd-5678')])
        self.assertIn('RequiresMountsFor=/ /srv/data',s);self.assertIn('--mountpoint /srv/data --source UUID=abcd-1234',s)
if __name__=='__main__':unittest.main()
