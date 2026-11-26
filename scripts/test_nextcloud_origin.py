import unittest
from nextcloud_origin import desired
class Tests(unittest.TestCase):
    def test_exact_private_origin(self):
        before={'trusted_domains':['localhost','127.0.0.1'],'overwritehost':None,'overwriteprotocol':None,'overwrite.cli.url':None}
        a=desired(before,'https://home.example.ts.net:19448')
        self.assertEqual(a['trusted_domains'],['localhost','127.0.0.1','home.example.ts.net:19448'])
        self.assertEqual(a['overwriteprotocol'],'https')
        self.assertEqual(desired(a,'https://home.example.ts.net:19448'),a)
        for u in ('http://home.example.ts.net:19448','https://evil.example:19448','https://home.example.ts.net:19448/path'):
            with self.assertRaises(ValueError):desired(before,u)
if __name__=='__main__':unittest.main()
