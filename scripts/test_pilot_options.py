import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
import pilot_options as p
class Tests(unittest.TestCase):
    def test_explicit_consent_and_password(self):
        valid={'services':['dns'],'consent':True,'dns_password':'independent-password'}
        self.assertEqual(p.validate(valid),(['dns'],'independent-password'))
        for change in ({'consent':False},{'services':['dns','dns']},{'dns_password':'short'},{'services':['arbitrary']},{'services':['invidious']}):
            with self.assertRaises(ValueError):p.validate({**valid,**change})
    def test_state_never_contains_password(self):
        with tempfile.TemporaryDirectory() as d:
            i=Path(d)
            with patch.object(p.subprocess,'run',return_value=Mock(returncode=0)),patch.object(p,'http_ready',return_value=True),patch.object(p,'dns_ready',return_value=True):
                self.assertEqual(p.provision(i,'192.168.1.168',['dns'],'independent-password'),{'dns':'ready'})
                self.assertNotIn('independent-password',(i/'.pilot-options.json').read_text())
                with self.assertRaises(ValueError):p.provision(i,'192.168.1.168',['dns'],'independent-password')
    def test_tailnet_url_is_official_only(self):
        for url,allowed in [('https://login.tailscale.com/a/abc123',True),('https://evil.example/a/abc',False),('https://login.tailscale.com.evil.example/a/abc',False)]:
            with patch.object(p.subprocess,'run',return_value=Mock(stdout=json.dumps({'BackendState':'NeedsLogin','AuthURL':url}))):
                self.assertEqual('url' in p.tailnet_status(),allowed)
    def test_existing_account_not_switched(self):
        with patch.object(p,'tailnet_status',return_value={'state':'Running'}),patch.object(p.subprocess,'run') as run:
            self.assertEqual(p.tailnet_connect(),{'state':'Running'})
            run.assert_not_called()

    def test_recheck_preserves_existing_state_and_never_provisions(self):
        with tempfile.TemporaryDirectory() as d:
            i=Path(d);(i/'deployment').mkdir()
            (i/'.pilot-options.json').write_text('{"dns":"starting","soulseek":"review"}')
            (i/'deployment/pilot-network.json').write_text('{"services":{"pilot-pihole":{}}}')
            with patch.object(p,'http_ready',return_value=True),patch.object(p,'dns_ready',return_value=True),patch.object(p.subprocess,'run') as run:
                self.assertEqual(p.reconcile(i),{'dns':'ready','soulseek':'review'})
                run.assert_not_called()

    def test_recheck_native_dns(self):
        with tempfile.TemporaryDirectory() as d:
            i=Path(d);(i/'deployment').mkdir()
            (i/'.pilot-options.json').write_text('{"dns":"review"}')
            (i/'.env').write_text('COMPOSE_PROFILES=music,dns\nDNS_WEB_PORT=18089\nDNS_LISTEN_PORT=1053\n')
            with patch.object(p,'http_ready',return_value=True),patch.object(p,'dns_ready',return_value=True):
                self.assertEqual(p.reconcile(i),{'dns':'ready'})
                (i/'.pilot-dns-native-pending').mkdir()
                self.assertEqual(p.reconcile(i),{'dns':'review'})
