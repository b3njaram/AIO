import tempfile
import unittest
from pathlib import Path

from restore import checksum, verified_archives


class BackupManifestTests(unittest.TestCase):
    def test_manifest_must_cover_every_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'instance.tar.gz'
            archive.write_bytes(b'fixture')
            manifest = root / 'SHA256SUMS'
            manifest.write_text(f'{checksum(archive)}  ./instance.tar.gz\n')
            self.assertEqual(verified_archives(root), {archive.name: archive})
            (root / 'jobbi-demo_files.tar.gz').write_bytes(b'volume')
            with self.assertRaisesRegex(ValueError, 'missing from SHA256SUMS'):
                verified_archives(root)

    def test_manifest_must_be_local_regular_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'other').touch()
            (root / 'SHA256SUMS').symlink_to(root / 'other')
            with self.assertRaisesRegex(ValueError, 'invalid backup checksum'):
                verified_archives(root)
