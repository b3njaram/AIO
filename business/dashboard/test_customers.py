import datetime as dt,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import server,customers
class Tests(unittest.TestCase):
    def test_registry_and_revocation(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(server,'HOME',Path(tmp)):
            server.save_order({'id':'ORDER','market':'US','total':'100'},True)
            with server.db() as db:
                customers.save(db,{'id':'HOME1','order_id':'ORDER','label':'Fixture'})
                def report():return {'schema':1,'kind':'jobbi-health-share','appliance_id':'HOME1','at':customers.now().isoformat(),'release':'a'*40,'free_percent':60,'temperature_c':40,'alerts':0,'backup':'verified','raid':'healthy','updates':'current'}
                with self.assertRaises(ValueError):customers.ingest(db,{'id':'HOME1','report':report()})
                customers.consent(db,{'id':'HOME1','allow':True,'confirmed':True})
                r=report();customers.ingest(db,{'id':'HOME1','report':r})
                self.assertEqual(customers.rows(db)[0]['state'],'reported_ok')
                with self.assertRaises(ValueError):customers.ingest(db,{'id':'HOME1','report':r})
                with self.assertRaises(ValueError):customers.ingest(db,{'id':'HOME1','report':{**report(),'password':'never'}})
                customers.consent(db,{'id':'HOME1','allow':False,'confirmed':True})
                self.assertIsNone(customers.rows(db)[0]['report'])
                with self.assertRaises(ValueError):customers.ingest(db,{'id':'HOME1','report':report()})
                self.assertEqual(db.execute('SELECT COUNT(*) FROM appliance_events').fetchone()[0],4)
    def test_reporting_credential(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(server,'HOME',Path(tmp)):
            server.save_order({'id':'ORDER','market':'US','total':'100'},True)
            with server.db() as db:
                customers.save(db,{'id':'HOME1','order_id':'ORDER','label':'Fixture'})
                with self.assertRaises(ValueError):customers.enable_reporting(db,{'id':'HOME1','confirmed':True})
                customers.consent(db,{'id':'HOME1','allow':True,'confirmed':True})
                grant=customers.enable_reporting(db,{'id':'HOME1','confirmed':True})
            def report():return {'schema':1,'kind':'jobbi-health-share','appliance_id':'HOME1','at':customers.now().isoformat(),'release':'a'*40,'free_percent':60,'temperature_c':40,'alerts':0,'backup':'verified','raid':'healthy','updates':'current'}
            with self.assertRaises(ValueError):
                with server.db() as db:customers.receive(db,report(),'x'*43)
            with server.db() as db:
                customers.receive(db,report(),grant['token'])
                self.assertTrue(customers.rows(db)[0]['reporting'])
                self.assertNotIn(grant['token'],str(customers.rows(db)))
            with self.assertRaises(ValueError):
                with server.db() as db:customers.receive(db,report(),grant['token'])
            with server.db() as db:customers.consent(db,{'id':'HOME1','allow':False,'confirmed':True})
            with self.assertRaises(ValueError):
                with server.db() as db:customers.receive(db,report(),grant['token'])
if __name__=='__main__':unittest.main()

