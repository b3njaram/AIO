#!/usr/bin/env python3
"""Short-lived local owner setup UI. Never expose this listener through Serve or a public proxy."""
import urllib.parse,ssl,ipaddress
import argparse,fcntl,hmac,http.server,importlib.util,json,os,re,secrets,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('account_setup',ROOT/'setup-accounts.py')
accounts=importlib.util.module_from_spec(spec);spec.loader.exec_module(accounts)
SUPPORTED=('music','movies','photos','files','tasks','monitor','passwords')
HTML=ROOT/'setup-web.html'
class Session:
    def __init__(self,instance,minutes=30,adapter=accounts):
        self.instance=instance;self.adapter=adapter
        self.env=adapter.env_for(instance)
        self.apps=[a for a in SUPPORTED if a in self.env['COMPOSE_PROFILES'].split(',')]
        self.token=secrets.token_urlsafe(32);self.deadline=time.monotonic()+minutes*60
        from account_progress import read
        self.done=set(read(instance))&set(self.apps);self.failed=[];self.lock=threading.Lock();self.closed=False
    def active(self):return not self.closed and time.monotonic()<self.deadline
    def status(self):return {'apps':self.apps,'done':sorted(self.done),'music_username':self.env.get('MUSIC_ADMIN','owner'),'failed':self.failed}
    def submit(self,d):
        if not self.active():raise ValueError('Setup session expired')
        if set(d)!={'app','username','email','password','confirm'}:raise ValueError('Invalid setup request')
        app,user,email,pw,confirm=(d[k] for k in ('app','username','email','password','confirm'))
        if not all(isinstance(x,str) for x in (app,user,email,pw,confirm)) or app not in [*self.apps,'all'] or not re.fullmatch('[A-Za-z0-9_.-]{1,48}',user) or not 3<=len(email)<=254 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email):raise ValueError('Invalid owner details')
        if app=='passwords':
            if pw or confirm:raise ValueError('Create the master password in the native Vaultwarden client')
        elif not 12<=len(pw)<=256 or pw!=confirm or '\x00' in pw:raise ValueError('Passwords must match and contain 12–256 characters')
        with self.lock:
            if not self.active():raise ValueError('Setup session expired')
            if app!='all' and app in self.done:raise ValueError('This step was already completed in this session')
            # Revalidate origin and instance before each operation. CLI uses the same lock.
            self.adapter.env_for(self.instance)
            with (self.instance/'.account-setup.lock').open('a') as guard:
                fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.failed=[]
                if app=='all':
                    for item in self.apps:
                        if item=='passwords' or item in self.done:continue
                        print('Configuring '+item,flush=True)
                        try:self.adapter.create(self.instance,item,user,email,pw);self.done.add(item);print(item+': account verified',flush=True)
                        except Exception:self.failed.append(item);print(item+': needs review',flush=True)
                elif app=='passwords':self.adapter.invite_vault(self.instance,email);self.done.add(app)
                else:
                    print('Configuring '+app,flush=True)
                    self.adapter.create(self.instance,app,user,email,pw);self.done.add(app)
                    print(app+': account verified',flush=True)
            return self.status()
class Server(http.server.ThreadingHTTPServer):
    # Wait for the current approved account operation and its response before exit.
    daemon_threads=False
    def __init__(self,port,session,bind='127.0.0.1',tls=None):
        super().__init__((bind,port),Handler);self.session=session;self.origin=('https://' if tls else 'http://')+bind+':'+str(self.server_port)
        if tls:self.socket=tls.wrap_socket(self.socket,server_side=True)
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def setup(self):
        super().setup();self.connection.settimeout(15)
    def send(self,status,payload,mime='application/json'):
        if not isinstance(payload,bytes):payload=json.dumps(payload).encode()
        self.send_response(status)
        for k,v in {'Content-Type':mime,'Content-Length':str(len(payload)),'Cache-Control':'no-store','Pragma':'no-cache','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'"}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(payload)
    def host_ok(self):return self.headers.get_all('Host',[])==[urllib.parse.urlsplit(self.server.origin).netloc]
    def authorized(self):
        s=self.server.session
        return s.active() and len(self.headers.get_all('Authorization',[]))==1 and hmac.compare_digest(self.headers['Authorization'],'Bearer '+s.token)
    def do_GET(self):
        if not self.host_ok():self.send(403,{'error':'Use exact local setup address'});return
        if not self.server.session.active():self.send(410,{'error':'Session closed'});return
        path=urllib.parse.urlsplit(self.path).path
        if path in ('/','/setup.js','/setup.css'):
            name,mime={'/':('setup-web.html','text/html; charset=utf-8'),'/setup.js':('setup-web.js','application/javascript; charset=utf-8'),'/setup.css':('setup-web.css','text/css; charset=utf-8')}[path]
            self.send(200,(ROOT/name).read_bytes(),mime);return
        if not self.authorized():self.send(401,{'error':'Local setup code required'});return
        if self.path=='/api/status':self.send(200,self.server.session.status())
        else:self.send(404,{'error':'Not found'})
    def do_POST(self):
        if not self.host_ok() or self.headers.get_all('Origin',[])!=[self.server.origin] or self.headers.get_all('X-Jobbi-Setup',[])!=['1'] or self.headers.get('Content-Type')!='application/json' or self.headers.get('Transfer-Encoding'):
            self.send(403,{'error':'Exact same-origin JSON request required'});return
        if not self.authorized():self.send(401,{'error':'Local setup code expired or invalid'});return
        try:
            lengths=self.headers.get_all('Content-Length',[])
            if len(lengths)!=1 or not 0<int(lengths[0])<=4096:raise ValueError()
            data=json.loads(self.rfile.read(int(lengths[0])))
            if not isinstance(data,dict):raise ValueError()
            if self.path=='/api/create':
                self.send(200,self.server.session.submit(data))
            elif self.path=='/api/finish' and data=={}:
                with self.server.session.lock:self.server.session.closed=True
                self.send(200,{'closed':True})
            else:self.send(404,{'error':'Not found'})
        except (OSError,ValueError,KeyError,TypeError,RuntimeError):
            # Do not echo application errors, passwords, request bodies or credentials.
            self.send(400,{'error':'Setup could not be completed. Check the owner details and local application state; existing passwords were not intentionally reset.'})
        except Exception:self.send(500,{'error':'Local application operation failed. Inspect the appliance privately.'})
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--port',type=int,default=17991);p.add_argument('--minutes',type=int,default=30);p.add_argument('--pilot-lan',type=Path,help='Root-prepared isolated pilot TLS configuration');a=p.parse_args()
    if os.geteuid()==0 or not 1024<=a.port<=65535 or not 5<=a.minutes<=60 or (not a.pilot_lan and not sys.stdout.isatty()):p.error('Use original non-root operator in an interactive terminal, 5–60 minutes')
    os.umask(0o077)
    session=Session(a.instance.resolve(),a.minutes)
    if session.env.get('OWNER_UID')!=str(os.getuid()):p.error('Use the original instance operator')
    if not session.apps:p.error('No supported account setup steps selected')
    if (session.instance/'.private-serve.json').exists() or any(x.get('url') for x in json.loads((session.instance/'dashboard.json').read_text())['apps']):p.error('Finish first-run accounts before enabling private HTTPS')
    bind='127.0.0.1';tls=None
    if a.pilot_lan:
        import stat
        cfg=a.pilot_lan.resolve();st=cfg.stat()
        if st.st_uid!=0 or st.st_mode&0o022 or cfg.is_symlink():p.error('Require root-prepared pilot configuration')
        spec=json.loads(cfg.read_text());bind=spec['address'];ip=ipaddress.IPv4Address(bind)
        if not any(ip in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):p.error('Only private IPv4 pilot addresses')
        if spec['instance']!=str(session.instance):p.error('Pilot instance mismatch')
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.minimum_version=ssl.TLSVersion.TLSv1_2
        tls.load_cert_chain(spec['cert'],spec['key'])
        print('Verify the HTTPS certificate SHA-256 fingerprint on your browser: '+spec['fingerprint'],flush=True)
    with Server(a.port,session,bind,tls) as server:
        print('One-time setup address:',server.origin)
        print('Setup code (do not share):',session.token,flush=True)
        print('Isolated pilot: use only the physically displayed HTTPS address and fingerprint.' if a.pilot_lan else 'For a remote technician browser, forward this exact loopback port over trusted SSH. Never publish via Serve/Funnel. Ctrl+C closes the session.')
        server.timeout=1
        try:
            while session.active():server.handle_request()
        except KeyboardInterrupt:pass
        finally:session.closed=True
    print('Setup session closed; perform native app acceptance and private access setup separately.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError) as e:sys.exit('Setup session unavailable: '+type(e).__name__)
