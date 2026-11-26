from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import importlib.util
import json
import unittest
from offline_media import inventory, verify_media

class MediaTests(unittest.TestCase):
    def test_manifest_and_corruption(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            sha='a'*40
            (root/'media.json').write_text(json.dumps(dict(schema=1,commit=sha,apps=['monitor'],os='ubuntu-24.04-amd64')))
            (root/'example.deb').write_bytes(b'package')
            (root/'SHA256SUMS').write_text(inventory(root))
            self.assertEqual(len(verify_media(root,sha,['monitor'])),64)
            (root/'example.deb').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify_media(root,sha,['monitor'])

    def test_offline_seed_uses_local_payload(self):
        spec=importlib.util.spec_from_file_location('usb',Path(__file__).with_name('make-install-usb.py'))
        usb=importlib.util.module_from_spec(spec);spec.loader.exec_module(usb)
        args=SimpleNamespace(name='home',operator='jobbi',commit='f'*40,data_uuid='abcd-1111',backup_uuid='abcd-2222',apps='monitor',ssh_key='test',media_sha='a'*64)
        seed=usb.config(args,'!')['autoinstall']
        self.assertEqual(seed['interactive-sections'],['storage'])
        self.assertNotIn('storage',seed)
        self.assertNotIn('packages',seed)
        self.assertEqual(seed['apt']['fallback'],'offline-install')
        files={f['path']:f['content'] for f in seed['user-data']['write_files']}
        self.assertTrue(json.loads(files['/etc/jobbi/install.json'])['offline'])
        self.assertNotIn('https://',files['/usr/local/sbin/jobbi-first-boot'])
        self.assertIn('release.bundle',files['/usr/local/sbin/jobbi-first-boot'])
        commands='\n'.join(seed['late-commands'])
        self.assertIn('chmod 0700 /target/var/lib/jobbi-offline',commands)
        self.assertIn('file:/var/lib/jobbi-offline-packages',commands)
        self.assertNotIn('file:/var/lib/jobbi-offline/packages',commands)
