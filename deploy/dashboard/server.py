import concurrent.futures
import json
import shutil
from urllib.parse import urlsplit
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
CONFIG = json.loads(Path('/app/config.json').read_text())
HTML = Path('/app/index.html').read_bytes()
def probe(app):
    if not app.get('probe'):
        return {'id': app['id'], 'state': 'manual'}
    try:
        with urllib.request.urlopen(app['probe'], timeout=3) as r:
            state = 'reachable' if r.status < 500 else 'unavailable'
    except urllib.error.HTTPError as e:
        state = 'reachable' if e.code < 500 else 'unavailable'
    except Exception:
        state = 'unavailable'
    return {'id': app['id'], 'state': state}
def account_status():
    try:
        p=Path('/storage/accounts.json')
        if p.is_symlink() or p.stat().st_size>4096:return {}
        d=json.loads(p.read_text())
        return {k:v for k,v in d.items() if k in 'music navidrome movies photos files passwords tasks monitor'.split() and v in ('verified','invited')}
    except (OSError,ValueError,AttributeError):return {}
def monitoring_status():
    try:
        p=Path('/storage/monitoring.json')
        if p.is_symlink() or p.stat().st_size>32768:return {}
        d=json.loads(p.read_text())
        return d if isinstance(d,dict) else {}
    except (OSError,ValueError):return {}
class Handler(BaseHTTPRequestHandler):
    def send(self, data, mime, status=200):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        self.path=urlsplit(self.path).path
        if self.path == '/':
            self.send(HTML, 'text/html; charset=utf-8')
        elif self.path in ('/manifest.webmanifest','/home.svg'):
            name,mime={'/manifest.webmanifest':('manifest.webmanifest','application/manifest+json'),'/home.svg':('home.svg','image/svg+xml')}[self.path]
            self.send((Path('/app')/name).read_bytes(),mime)
        elif self.path == '/api/config':
            safe = {'name':CONFIG['name'], 'apps':[{k:v for k,v in a.items() if k!='probe'} for a in CONFIG['apps']]}
            self.send(json.dumps(safe).encode(), 'application/json')
        elif self.path == '/api/status':
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                states = list(pool.map(probe, CONFIG['apps']))
            d = shutil.disk_usage('/storage')
            self.send(json.dumps({'apps':states,'disk':{'total':d.total,'used':d.used,'free':d.free}}).encode(), 'application/json')
        elif self.path == '/api/health':
            try:
                path=Path('/storage/health.json')
                if path.is_symlink() or path.stat().st_size>65536:raise ValueError()
                state=json.loads(path.read_text())
                if not isinstance(state,dict):raise ValueError()
                # Host writes a sanitized snapshot; this endpoint does not execute commands.
                self.send(json.dumps({**state,'accounts':account_status(),'monitoring':monitoring_status()}).encode(),'application/json')
            except (OSError,ValueError):self.send(json.dumps({'state':'not_configured','accounts':account_status()}).encode(),'application/json')
        elif self.path == '/healthz':
            self.send(b'ok\n','text/plain')
        else:
            self.send(b'Not found\n','text/plain',404)
ThreadingHTTPServer(('0.0.0.0',8080), Handler).serve_forever()
