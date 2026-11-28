import json,tempfile,unittest
from pathlib import Path
from account_progress import read,record
class AccountProgressTests(unittest.TestCase):
    def test_verified_music_and_invited_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'data/.dashboard-metrics').mkdir(parents=True)
            self.assertEqual(read(p),{})
            record(p,'music');record(p,'passwords','invited')
            self.assertEqual(read(p),{'music':'verified','navidrome':'verified','passwords':'invited'})
            with self.assertRaises(ValueError):record(p,'passwords','secret')
            self.assertNotIn('secret',(p/'data/.dashboard-metrics/accounts.json').read_text())
