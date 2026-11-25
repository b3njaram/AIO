#!/usr/bin/env python3
"""Customer-initiated, expiring, read-only diagnostic session on the owner's tailnet."""
import argparse,datetime as dt,fcntl,hmac,http.server,importlib.util,json,os,re,secrets,ssl,stat,subprocess,sys,time
from pathlib import Path
from maintenance_alerts import tailnet_address
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('health_share',ROOT/'share-health.py')
share=importlib.util.module_from_spec(spec);spec.loader.exec_module(share)
def owner(i):
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or env.get('INSTANCE_DIR')!=str(i) or env.get('OWNER_UID')!=str(os.getuid()):raise ValueError('Original non-root appliance operator required')
def identity(status):
    me=status['Self'];host=me['DNSName'].rstrip('.').lower()
    ips=me['TailscaleIPs']
    if status['BackendState']!='Running' or not me.get('Online') or not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+\.ts\.net',host):raise ValueError('Customer tailnet must be active')
    addresses=[x for x in ips if ':' not in x and tailnet_address(x)]
    if len(addresses)!=1:raise ValueError('Require exact tailnet IPv4 address')
    return host,addresses[0]
def history(i,event):
    if event not in ('started','report_viewed','expired','revoked','closed'):raise ValueError('Invalid event')
    fd=os.open(i/'.support-history.jsonl',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    with os.fdopen(fd,'a') as out:
        st=os.fstat(out.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077:raise ValueError('Unsafe support audit file')
        out.write(json.dumps({'at':dt.datetime.now(dt.timezone.utc).isoformat(),'event':event})+'\n')
        out.flush()
def tls_context(cert,key,host):
    for p in (cert,key):
        st=p.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o022:raise ValueError('Use reviewed owner-owned TLS files')
    if key.stat().st_mode&0o077:raise ValueError('Keep TLS private key mode 0600')
    data=ssl._ssl._test_decode_cert(str(cert))
    if ('DNS',host) not in data.get('subjectAltName',()) or ssl.cert_time_to_seconds(data['notAfter'])<=time.time()+3600:raise ValueError('Certificate must match this tailnet hostname and remain valid')
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.minimum_version=ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(str(cert),str(key));return ctx
class Session:
    def __init__(self,instance,id,minutes,read=share.report,record=history):
        self.instance=instance;self.id=id;self.token=secrets.token_urlsafe(32);self.deadline=time.monotonic()+minutes*60;self.closed=False;self.read=read;self.record=record
    def active(self):return not self.closed and time.monotonic()<self.deadline
    def report(self):
        if not self.active():raise ValueError('Session expired')
        data=self.read(self.instance,self.id)
        self.record(self.instance,'report_viewed')
        return data
class Server(http.server.HTTPServer):
    def __init__(self,ip,port,host,session,context=None):
        self.session=session
        super().__init__((ip,port),Handler)
        self.host_header=host+':'+str(self.server_port)
        self.context=context
    def get_request(self):
        sock,addr=super().get_request();sock.settimeout(5)
        if self.context:
            try:sock=self.context.wrap_socket(sock,server_side=True)
            except BaseException:sock.close();raise
        return sock,addr
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status,data,mime='application/json'):
        body=data if isinstance(data,bytes) else json.dumps(data).encode()
        self.send_response(status)
        for k,v in {'Content-Type':mime,'Content-Length':str(len(body)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; script-src 'self'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'"}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.headers.get_all('Host',[])!=[self.server.host_header]:self.send(403,{'error':'Exact private hostname required'});return
        session=self.server.session
        if not session.active():self.send(410,{'error':'Session expired'});return
        assets={'/':('support-session.html','text/html; charset=utf-8'),'/support.js':('support-session.js','application/javascript; charset=utf-8')}
        if self.path in assets:
            file,mime=assets[self.path];self.send(200,(ROOT/file).read_bytes(),mime);return
        if self.path!='/api/report':self.send(404,{'error':'Not found'});return
        auth=self.headers.get_all('Authorization',[])
        if len(auth)!=1 or not hmac.compare_digest(auth[0],'Bearer '+session.token):self.send(401,{'error':'Customer session code required'});return
        try:self.send(200,session.report())
        except (OSError,ValueError,KeyError,TypeError):self.send(503,{'error':'Fresh diagnostics unavailable'})
    def do_POST(self):self.send(405,{'error':'Read-only session'})
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('action',choices=['start','history']);p.add_argument('--appliance-id');p.add_argument('--cert',type=Path);p.add_argument('--key',type=Path);p.add_argument('--port',type=int,default=17992);p.add_argument('--minutes',type=int,default=30);p.add_argument('--approve',action='store_true');a=p.parse_args()
    i=a.instance.resolve();owner(i);os.umask(0o077)
    if a.action=='history':
        path=i/'.support-history.jsonl'
        if path.is_file() and not path.is_symlink():
            for line in path.read_text().splitlines()[-100:]:
                row=json.loads(line);print(row['at'],row['event'])
        return
    if not a.appliance_id or not a.cert or not a.key or not 1024<=a.port<=65535 or not 5<=a.minutes<=60:p.error('Specify appliance ID, matching TLS certificate/key and 5–60 minute duration')
    host,ip=identity(json.loads(subprocess.check_output(['tailscale','status','--json'],text=True,timeout=15)))
    context=tls_context(a.cert.absolute(),a.key.absolute(),host)
    share.report(i,a.appliance_id)
    if not a.approve:print('Preview: private TLS diagnostic-only session; confirm customer ACLs, no Funnel, no shell and no application data. Add --approve.');return
    if not sys.stdin.isatty() or not sys.stdout.isatty():p.error('Customer must authorize in a trusted interactive terminal')
    with (i/'.support-session.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        session=Session(i,a.appliance_id,a.minutes)
        with Server(ip,a.port,host,session,context) as server:
            history(i,'started')
            print('Private diagnostic session:', 'https://'+server.host_header)
            print('Customer session code:',session.token,flush=True)
            print('Share with the intended technician only. Ctrl+C revokes. No shell or changes permitted.')
            server.timeout=0.5
            event='closed'
            try:
                while session.active():server.handle_request()
                event='expired'
            except KeyboardInterrupt:event='revoked'
            finally:
                session.closed=True;history(i,event)
    print('Session closed.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as e:sys.exit('Support session unavailable: '+type(e).__name__)
