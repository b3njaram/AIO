"""Exercise the real HTTP handler without requiring a container."""
import importlib.util,json,tempfile,threading,unittest,urllib.request
from pathlib import Path
from unittest.mock import patch
class Tests(unittest.TestCase):
    def test_monitor_summary_available_without_health_snapshot(self):
        source=Path(__file__).resolve().parents[1]/'deploy/dashboard/server.py'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=root/'app';storage=root/'storage';app.mkdir();storage.mkdir()
            (app/'config.json').write_text('{"name":"fixture","apps":[]}')
            (app/'index.html').write_text('fixture')
            (storage/'monitoring.json').write_text('{"state":"available","monitors":{"dashboard":{"samples":3}}}')
            (storage/'accounts.json').write_text('{"music":"verified"}')
            # Replace only fixture filesystem paths; remove top-level listener startup.
            code=source.read_text().replace("Path('/app",f"Path('{app}").replace("Path('/storage",f"Path('{storage}")
            code=code.rsplit("ThreadingHTTPServer(('0.0.0.0',8080), Handler).serve_forever()",1)[0]
            ns={};exec(compile(code,str(source),'exec'),ns)
            server=ns['ThreadingHTTPServer'](('127.0.0.1',0),ns['Handler'])
            t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
            try:
                for invalid in (None,'broken','[]','{"data_free_percent":42}'):
                    p=storage/'health.json'
                    if invalid is None:p.unlink(missing_ok=True)
                    else:p.write_text(invalid)
                    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/health',timeout=3) as resp:
                        d=json.load(resp)
                    self.assertEqual(d['monitoring']['monitors']['dashboard']['samples'],3)
                    self.assertEqual(d['accounts'],{'music':'verified'})
                    if invalid!='{"data_free_percent":42}':self.assertEqual(d['state'],'not_configured')
            finally:server.shutdown();server.server_close();t.join()
