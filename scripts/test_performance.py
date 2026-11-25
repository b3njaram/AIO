import unittest
from performance import capacity,cpu_plan
import os,tempfile
from pathlib import Path
from unittest.mock import patch
class Tests(unittest.TestCase):
    def test_capacity(self):
        self.assertFalse(capacity(16,4,{'music','files'})['ram_review'])
        self.assertTrue(capacity(8,2,{'photos','movies','files'})['ram_review'])
        self.assertEqual(capacity(32,8,{'photos','movies','files','music','tasks','passwords','monitor'})['suggested_ram_gib'],32)
    def test_unknown_profile(self):
        with self.assertRaises(KeyError):capacity(16,4,{'unknown'})
    def test_cpu_plan(self):
        with tempfile.TemporaryDirectory() as tmp,patch('performance.os.geteuid',return_value=1000):
            i=Path(tmp);(i/'deployment').mkdir()
            (i/'deployment/compose.yaml').write_text('cpu_shares: ${JOBBI_BACKGROUND_CPU_SHARES:-1024}\n'*2)
            e=i/'.env';e.write_text(f'INSTANCE_DIR={i}\nOWNER_UID={os.getuid()}\nCOMPOSE_PROFILES=photos,music\nPRIVATE_VALUE=unchanged\n');e.chmod(0o600)
            services,shares,body=cpu_plan(i,'foreground')
            self.assertEqual(shares,256);self.assertEqual(len(services),2)
            self.assertIn('PRIVATE_VALUE=unchanged',body);self.assertNotIn('JOBBI_BACKGROUND_CPU_SHARES',e.read_text())
            self.assertEqual(cpu_plan(i,'balanced')[1],1024)
            (i/'.upgrade-hold.json').touch()
            with self.assertRaises(ValueError):cpu_plan(i,'foreground')
if __name__=='__main__':unittest.main()

