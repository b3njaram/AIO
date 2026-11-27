import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pilot_tailnet as m
class Tests(unittest.TestCase):
    def test_host_validation(self):
        self.assertEqual(m.hostname('Customer.Example.ts.net.'),'customer.example.ts.net')
        for h in (None,'ts.net','customer.example.ts.net.evil','https://customer.example.ts.net','customer.example.ts.net:443'):
            with self.assertRaises(ValueError):m.hostname(h)
    def test_explicit_approval_and_retained_failed_state(self):
        with tempfile.TemporaryDirectory() as d:
            i=Path(d)/'laptop-test';i.mkdir();(i/'.env').write_text('INSTANCE_DIR='+str(i)+'\n');(i/'dashboard.json').write_text('{"apps":[]}')
            status={'state':'Running','host':'customer.example.ts.net'}
            with patch.object(m,'eligibility'),patch.object(m.subprocess,'run') as run:
                with self.assertRaises(ValueError):m.finish(i,{'consent':False,'host':status['host']},status,{})
                with self.assertRaises(ValueError):m.finish(i,{'consent':True,'host':'other.example.ts.net'},status,{})
                run.assert_not_called()
                self.assertEqual(m.finish(i,{'consent':True,'host':status['host']},status,{}),'https://customer.example.ts.net:19443/')
                approval=json.loads((i/m.APPROVAL).read_text())
                self.assertEqual(approval['host'],status['host'])
                self.assertEqual((i/m.APPROVAL).stat().st_mode&0o077,0)
                with self.assertRaises(ValueError):m.finish(i,{'consent':True,'host':status['host']},status,{})
                run.assert_called_once()
    def test_invidious_refusal_and_verified_accounts(self):
        with tempfile.TemporaryDirectory() as d:
            i=Path(d)/'laptop-test';i.mkdir()
            e={'INSTANCE_DIR':str(i),'BIND_IP':'127.0.0.1','COMPOSE_PROJECT_NAME':'jobbi-laptop-test','OWNER_UID':'1000'}
            c={'apps':[{'id':'music'},{'id':'navidrome'},{'id':'passwords'}]}
            with patch.object(m.os,'getuid',return_value=1000),patch.object(m.os,'geteuid',return_value=1000),patch.object(m,'accounts',return_value={'music':'verified','navidrome':'verified','passwords':'invited'}):
                m.eligibility(i,e,c,{})
                with self.assertRaises(ValueError):m.eligibility(i,e,c,{'invidious':'ready'})
                with self.assertRaises(ValueError):m.eligibility(i,e,c,{'soulseek':'review'})
