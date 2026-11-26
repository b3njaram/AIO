#!/usr/bin/env python3
"""Short-lived customer-owned management session over local SSH tunnel only."""
import argparse,http.server,importlib.util,json,os,secrets,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),ROOT/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('setup-web');apps=load('app-manager');share=load('share-health')
class Session:
    def __init__(self,i,minutes,adapter=apps):
        self.instance=i;self.adapter=adapter;self.token=secrets.token_urlsafe(32);self.deadline=time.monotonic()+minutes*60;self.closed=False;self.lock=threading.Lock()
    def active(self):return not self.closed and time.monotonic()<self.deadline
class Handler(base.Handler):
    def do_GET(self):
        if not self.host_ok():self.send(403,{'error':'Wrong local host'});return
        if not self.server.session.active():self.send(410,{'error':'Session closed'});return
        assets={'/':('manage-web.html','text/html; charset=utf-8'),'/manage.js':('manage-web.js','application/javascript; charset=utf-8'),'/setup.css':('setup-web.css','text/css; charset=utf-8')}
        if self.path in assets:
            name,mime=assets[self.path];self.send(200,(ROOT/name).read_bytes(),mime);return
        if not self.authorized():self.send(401,{'error':'Session code required'});return
        try:
            s=self.server.session
            if self.path=='/api/status':self.send(200,{'apps':s.adapter.status(s.instance)})
            else:self.send(404,{'error':'Not found'})
        except Exception:self.send(503,{'error':'Status unavailable'})
    def do_POST(self):
        if not self.host_ok() or self.headers.get_all('Origin',[])!=[self.server.origin] or self.headers.get_all('X-Jobbi-Setup',[])!=['1'] or self.headers.get_all('Content-Type',[])!=['application/json'] or self.headers.get('Transfer-Encoding'):
            self.send(403,{'error':'Same-origin JSON required'});return
        if not self.authorized():self.send(401,{'error':'Session code required'});return
        try:
            lengths=self.headers.get_all('Content-Length',[])
            if len(lengths)!=1 or not 0<int(lengths[0])<=2048:raise ValueError()
            d=json.loads(self.rfile.read(int(lengths[0])));s=self.server.session
            with s.lock:
                if not s.active():raise ValueError()
                if self.path=='/api/restart' and set(d)=={'app','confirm'} and d['confirm'] is True:self.send(200,s.adapter.restart(s.instance,d['app'],True))
                elif self.path=='/api/report' and set(d)=={'id','confirm'} and d['confirm'] is True:self.send(200,share.report(s.instance,d['id']))
                elif self.path=='/api/finish' and d=={}:s.closed=True;self.send(200,{'closed':True})
                else:self.send(400,{'error':'Unsupported operation or missing consent'})
        except Exception:self.send(400,{'error':'Operation refused or unavailable. Review locally.'})
class Server(http.server.ThreadingHTTPServer):
    daemon_threads=False
    def __init__(self,port,session):
        super().__init__(('127.0.0.1',port),Handler);self.session=session;self.origin='http://127.0.0.1:'+str(self.server_port)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--minutes',type=int,default=30);a=p.parse_args();i=a.instance.resolve()
    if not sys.stdout.isatty() or not 5<=a.minutes<=60:p.error('Use an interactive operator terminal')
    apps.identity(i);os.umask(0o077);session=Session(i,a.minutes)
    with Server(17994,session) as server:
        print('Local management:',server.origin,'\nSession code:',session.token,flush=True)
        print('Use a trusted SSH tunnel. Never publish through Serve, Funnel or proxy.')
        server.timeout=1
        try:
            while session.active():server.handle_request()
        except KeyboardInterrupt:pass
        finally:session.closed=True
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError) as e:sys.exit('Management unavailable: '+type(e).__name__)
