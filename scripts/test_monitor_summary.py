import datetime as dt,importlib.util,sqlite3,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('monitor_summary',Path(__file__).with_name('monitor-summary.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_missing_and_bounded_private_data(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'kuma.db';now=dt.datetime(2026,11,27,0,0,tzinfo=dt.timezone.utc)
            self.assertEqual(m.summarize(db,now)['state'],'unavailable')
            with sqlite3.connect(db) as c:
                c.executescript('CREATE TABLE monitor(id INTEGER,name TEXT,active INTEGER,url TEXT);CREATE TABLE heartbeat(id INTEGER,monitor_id INTEGER,status INTEGER,ping INTEGER,time TEXT,msg TEXT);')
                c.executemany('INSERT INTO monitor VALUES(?,?,?,?)',[(1,'Jobbi Home · music',1,'secret-url'),(2,'private monitor',1,'secret-url')])
                c.executemany('INSERT INTO heartbeat VALUES(?,?,?,?,?,?)',[(1,1,1,20,'2026-11-26 12:00:00','secret'),(2,1,0,0,'2026-11-26 13:00:00','secret'),(3,1,1,30,'2026-11-26 14:00:00','secret'),(4,1,1,100,'2026-11-25 14:00:00','secret'),(5,2,1,10,'2026-11-26 14:00:00','secret')])
            out=m.summarize(db,now)
            self.assertEqual(out['state'],'available')
            self.assertEqual(set(out['monitors']),{'music'})
            self.assertEqual(out['monitors']['music'],{'state':'up','samples':3,'success_percent':66.67,'avg_ms':25.0,'recent':[1,0,1]})
            self.assertNotIn('secret',str(out))
