import unittest,tempfile,threading,urllib.request,urllib.error,base64,json
from pathlib import Path
from unittest.mock import patch
import server
class DashboardTests(unittest.TestCase):
    def test_orders_and_cash(self):
        with tempfile.TemporaryDirectory() as p,patch.object(server,'HOME',Path(p)):
            server.save_order({'id':'TEST','market':'MX','total':'1000','stage':'delivered','delivered':'2025-01-01','months':6,'hardware_condition':'new'},True)
            server.payment({'id':'TEST','transaction':'TX1','kind':'deposit','amount':'400'})
            x=server.list_orders()[0]
            self.assertEqual(x['due'],60000)
            self.assertEqual(x['support_end'],'2025-07-01')
            self.assertEqual(x['warranty_end'],'2026-01-01')
            with self.assertRaises(ValueError):server.payment({'id':'TEST','transaction':'TX2','kind':'refund','amount':'401'})
    def test_cost(self):
        x=server.costing(dict(market='US',hardware='500',labor='90',support='60',shipping='20',warranty='25',overhead='10',months='6'))
        self.assertEqual(x['price'],'809.00')
        self.assertEqual(x['contribution'],'104.00')
    def test_http_protection(self):
        with tempfile.TemporaryDirectory() as p,patch.object(server,'HOME',Path(p)),patch.object(server,'REPORTS',Path(p)/'sourcing'):
            http=server.http.server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
            http.password='test-secret-for-ci'
            t=threading.Thread(target=http.serve_forever,daemon=True);t.start()
            base='http://127.0.0.1:'+str(http.server_port)
            auth='Basic '+base64.b64encode(b'owner:test-secret-for-ci').decode()
            try:
                with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(base+'/api/init')
                self.assertEqual(e.exception.code,401)
                with urllib.request.urlopen(urllib.request.Request(base+'/api/init',headers={'Authorization':auth})) as r:self.assertIn('profiles',json.load(r))
                with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(urllib.request.Request(base+'/api/search',data=b'{}',headers={'Authorization':auth,'Content-Type':'application/json'}))
                self.assertEqual(e.exception.code,403)
            finally:http.shutdown();http.server_close();t.join()
if __name__=='__main__':unittest.main()
