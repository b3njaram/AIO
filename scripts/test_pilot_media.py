import unittest
from pathlib import Path
from pilot_media import credentials,soulseek,invidious,pinned
class Tests(unittest.TestCase):
    def test_per_appliance(self):
        a,b=credentials(),credentials()
        self.assertNotEqual(a['username'],b['username'])
        self.assertNotEqual(a['password'],a['api_key'])
        s=soulseek(Path('/srv/jobbi-data/laptop-test'),1000,1000,a)
        self.assertNotIn('ports',s['slskd'])
        self.assertIn('/shares:ro',s['slskd']['volumes'][1])
        self.assertEqual(s['jobbi-music']['environment']['SLSKD_API_KEY'],a['api_key'])
    def test_invidious_isolated(self):
        pins={k:repo+'@sha256:'+'a'*64 for k,repo in [('invidious','quay.io/invidious/invidious'),('companion','quay.io/invidious/invidious-companion'),('postgres','docker.io/library/postgres')]}
        c=invidious(Path('/tmp/lab'),pins,Path('/tmp/source'),{'db':'a'*48,'hmac':'b'*48,'companion':'c'*48})
        self.assertEqual(c['services']['invidious']['ports'],['127.0.0.1:18091:3000'])
        self.assertNotIn('ports',c['services']['invidious-db'])
        self.assertNotIn('ports',c['services']['invidious-companion'])
        with self.assertRaises(ValueError):pinned('quay.io/invidious/invidious:latest','quay.io/invidious/invidious')
