import unittest
from pilot_media import public_origin,local_fallback_source
class Tests(unittest.TestCase):
    def test_origin(self):
        self.assertEqual(public_origin('https://192.168.1.168:18091/'),'https://192.168.1.168:18091')
        for u in ('https://yt.jobbisoft.com.mx:18091','http://192.168.1.168:18091','https://192.168.1.168:18091/?x=1','https://8.8.8.8:18091'):
            with self.assertRaises(ValueError):public_origin(u)
    def test_patch(self):
        s=local_fallback_source('  const raw=[env.INVIDIOUS_URL];\nnormalizeInvidiousResults(raw,origin);')
        self.assertIn("return ['http://invidious:3000']",s)
        self.assertIn('JOBBI_INVIDIOUS_PUBLIC_ORIGIN',s)
