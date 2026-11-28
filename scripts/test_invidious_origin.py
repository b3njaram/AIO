import json,tempfile,unittest
from pathlib import Path
import invidious_origin as m

class Tests(unittest.TestCase):
    def test_migrate_preserves_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            i=Path(d);(i/'deployment').mkdir()
            state=i/'data/pilot-media';state.mkdir(parents=True)
            (state/'invidious-adapter.before').write_text('fixture')
            p=i/'deployment/pilot-media.json'
            cfg={'domain':'192.168.1.5','external_port':18091,'https_only':True,'hmac_key':'secret'}
            music={'JOBBI_LOCAL_INVIDIOUS':'true','JOBBI_INVIDIOUS_PUBLIC_ORIGIN':'https://192.168.1.5:18091','INVIDIOUS_URL':'disabled','INVIDIOUS_BACKUPS':'','SLSKD_API_KEY':'other-secret'}
            original={'services':{'invidious':{'ports':['127.0.0.1:18091:3000'],'environment':{'INVIDIOUS_CONFIG':json.dumps(cfg)}},'invidious-db':{},'invidious-companion':{},'jobbi-music':{'environment':music}}}
            p.write_text(json.dumps(original));p.chmod(0o600)
            after=json.loads(m.desired(i,'https://customer.example.ts.net:19453'))['services']
            self.assertEqual(after['jobbi-music']['environment']['SLSKD_API_KEY'],'other-secret')
            self.assertEqual(after['jobbi-music']['environment']['JOBBI_INVIDIOUS_PUBLIC_ORIGIN'],'https://customer.example.ts.net:19453')
            new=json.loads(after['invidious']['environment']['INVIDIOUS_CONFIG'])
            self.assertEqual((new['domain'],new['external_port'],new['hmac_key']),('customer.example.ts.net',19453,'secret'))
            self.assertEqual(json.loads(p.read_text()),original)
            original['services']['invidious-companion']['ports']=['0.0.0.0:8282:8282']
            p.write_text(json.dumps(original))
            with self.assertRaises(ValueError):m.desired(i,'https://customer.example.ts.net:19453')
