import io,tarfile,tempfile,unittest
from pathlib import Path
from restore import validate_archive
class Tests(unittest.TestCase):
    def test_optional_state_rejected_during_archive_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            archive=Path(d)/'instance.tar.gz'
            for name in ('deployment/pilot-media.json','deployment/pilot-network.json','data/pilot-media/slskd/state','data/pilot-pihole/pihole.toml'):
                with tarfile.open(archive,'w:gz') as t:
                    for n in ('.env','dashboard.json','release.json','deployment/compose.yaml',name):
                        info=tarfile.TarInfo(n);info.size=2;t.addfile(info,io.BytesIO(b'{}'))
                with self.assertRaisesRegex(ValueError,'Optional-service archive'):
                    validate_archive(archive,instance=True)
