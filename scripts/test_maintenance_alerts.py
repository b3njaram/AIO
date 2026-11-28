import datetime as dt,tempfile,unittest,os
from pathlib import Path
from unittest.mock import Mock,patch
import maintenance_alerts as m
class Tests(unittest.TestCase):
    def snapshot(self):
        return {'at':m.now().isoformat(),'data_free_percent':10,'docker_free_percent':30,'temperature_c':[90],'drives':[{'state':'failed','temperature_c':65}],'backup':{'state':'mount_unavailable'},'storage':{'redundancy':{'state':'degraded'}},'service_alert_count':1}
    def test_categories(self):
        s=self.snapshot()
        self.assertEqual(set(m.alerts(s)),{'storage_low','temperature_high','drive_failed','backup_missing','raid_degraded','services_review'})
        s['at']='2000-01-01T00:00:00+00:00';self.assertEqual(m.alerts(s),['health_stale'])
    def test_url(self):
        self.assertEqual(m.private_url('https://notify.demo.ts.net/fixture-topic'),'https://notify.demo.ts.net/fixture-topic')
        for x in ('http://notify.demo.ts.net/fixture-topic','https://example.com/fixture-topic','https://notify.demo.ts.net:8080/fixture-topic','https://user@notify.demo.ts.net/fixture-topic','https://notify.demo.ts.net/fixture-topic?token=x'):
            with self.assertRaises(ValueError):m.private_url(x)
    def test_public_address_refused(self):
        self.assertTrue(m.tailnet_address('100.100.1.2'))
        self.assertFalse(m.tailnet_address('192.168.1.2'))
        conn=m.PrivateHTTPS('notify.demo.ts.net',443)
        with patch.object(m.socket,'getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]),patch.object(m.socket,'create_connection') as connect:
            with self.assertRaises(ValueError):conn.connect()
            connect.assert_not_called()
    def test_consent_and_dedup(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(m.os,'geteuid',return_value=1000):
            i=Path(tmp);send=Mock()
            self.assertEqual(m.process(i,self.snapshot(),send)['delivery'],'disabled')
            m.atomic(i/'.notification-config.json',{'enabled':True,'url':'https://notify.demo.ts.net/fixture-topic','token':'fixture-token-123456789'})
            self.assertEqual(m.process(i,self.snapshot(),send)['delivery'],'sent')
            self.assertEqual(m.process(i,self.snapshot(),send)['delivery'],'ready')
            send.assert_called_once()
            (i/'.notification-config.json').unlink()
            self.assertEqual(m.process(i,self.snapshot(),send)['delivery'],'disabled')
if __name__=='__main__':unittest.main()
