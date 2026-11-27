import json
import tempfile
import shutil
import subprocess
import unittest
from pathlib import Path
from pilot_media import SOULSEEK_LOGIN_PROBE,SLSKD,credentials,soulseek,invidious,invidious_credentials,pinned,existing_media,merge_services
class Tests(unittest.TestCase):
    def test_per_appliance(self):
        a,b=credentials(),credentials()
        self.assertNotEqual(a['username'],b['username'])
        self.assertNotEqual(a['password'],a['api_key'])
        s=soulseek(Path('/srv/jobbi-data/laptop-test'),1000,1000,a)
        self.assertNotIn('ports',s['slskd'])
        self.assertEqual(s['slskd']['build']['args']['BASE_IMAGE'],SLSKD)
        self.assertEqual(s['slskd']['build']['dockerfile'],'Dockerfile.slskd')
        self.assertIn('/shares:ro',s['slskd']['volumes'][1])
        self.assertEqual(s['jobbi-music']['environment']['SLSKD_API_KEY'],a['api_key'])
    @unittest.skipUnless(shutil.which('node'), 'Node is required to run the exact container probe')
    def test_soulseek_requires_authenticated_server_state(self):
        for connected, authenticated in ((True, False), (False, True), (True, True)):
            state = json.dumps({'isConnected': connected, 'isLoggedIn': authenticated})
            stub = 'globalThis.fetch = async () => ({ok:true, json:async () => (' + state + ')});'
            result = subprocess.run(['node', '--input-type=module', '-e', stub + SOULSEEK_LOGIN_PROBE], timeout=10)
            self.assertEqual(result.returncode, 0 if connected and authenticated else 1)

    def test_builtin_invidious_manifest_uses_exact_images(self):
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'deploy/invidious-pilot.json').read_text())
        self.assertRegex(manifest['source_commit'],r'^[a-f0-9]{40}$')
        built=invidious(Path('/tmp/lab'),manifest['images'],Path('/tmp/source'),
                        {'db':'a'*48,'hmac':'b'*48,'companion':'c'*16})
        for key, service in [('invidious','invidious'),('companion','invidious-companion'),('postgres','invidious-db')]:
            entry=built['services'][service]
            image=entry['image'] if 'image' in entry else entry['build']['args']['BASE_IMAGE']
            self.assertEqual(image,manifest['images'][key])

    def test_invidious_isolated(self):
        pins={k:repo+'@sha256:'+'a'*64 for k,repo in [('invidious','quay.io/invidious/invidious'),('companion','quay.io/invidious/invidious-companion'),('postgres','docker.io/library/postgres')]}
        c=invidious(Path('/tmp/lab'),pins,Path('/tmp/source'),{'db':'a'*48,'hmac':'b'*48,'companion':'c'*16})
        self.assertEqual(c['services']['invidious']['ports'],['127.0.0.1:18091:3000'])
        self.assertNotIn('ports',c['services']['invidious-db'])
        self.assertNotIn('ports',c['services']['invidious-companion'])
        companion=c['services']['invidious-companion']
        self.assertRegex(invidious_credentials()['companion'],r'^[A-Za-z0-9]{16}$')
        self.assertEqual(companion['environment']['SERVER_SECRET_KEY'],'c'*16)
        with self.assertRaises(ValueError):
            invidious(Path('/tmp/lab'),pins,Path('/tmp/source'),{'db':'a'*48,'hmac':'b'*48,'companion':'c'*48})
        self.assertTrue(companion['read_only'])
        self.assertEqual(companion['volumes'],['pilot-invidious-companion-cache:/var/tmp/youtubei.js:rw'])
        self.assertIn('pilot-invidious-companion-cache',c['volumes'])
        self.assertEqual(c['services']['invidious']['depends_on']['invidious-db']['condition'],'service_healthy')
        self.assertIn('127.0.0.1',c['services']['invidious-db']['healthcheck']['test'])
        with self.assertRaises(ValueError):pinned('quay.io/invidious/invidious:latest','quay.io/invidious/invidious')

    def test_add_second_provider_without_replacing_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            i=Path(d);state=i/'state';state.mkdir();overlay=i/'overlay.json'
            overlay.write_text(json.dumps({'services':{'slskd':{},'jobbi-music':{'environment':{'SLSKD_API_KEY':'retained'}}}}))
            config=existing_media(overlay,state,False,True)
            merge_services(config,{'invidious':{},'jobbi-music':{'environment':{'JOBBI_LOCAL_INVIDIOUS':'true'}}})
            self.assertEqual(config['services']['jobbi-music']['environment'],{'SLSKD_API_KEY':'retained','JOBBI_LOCAL_INVIDIOUS':'true'})
            with self.assertRaises(ValueError):existing_media(overlay,state,True,False)
            (state/'invidious-source').mkdir()
            with self.assertRaises(ValueError):existing_media(overlay,state,False,True)
            with self.assertRaises(ValueError):merge_services(config,{'jobbi-music':{'environment':{'SLSKD_API_KEY':'replace'}}})
