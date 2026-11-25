import unittest
from performance import capacity
class Tests(unittest.TestCase):
    def test_capacity(self):
        self.assertFalse(capacity(16,4,{'music','files'})['ram_review'])
        self.assertTrue(capacity(8,2,{'photos','movies','files'})['ram_review'])
        self.assertEqual(capacity(32,8,{'photos','movies','files','music','tasks','passwords','monitor'})['suggested_ram_gib'],32)
    def test_unknown_profile(self):
        with self.assertRaises(KeyError):capacity(16,4,{'unknown'})
if __name__=='__main__':unittest.main()
