#!/usr/bin/env python3
"""Optional private-only report receiver; no business read or admin endpoints."""
import argparse,http.server,importlib.util,json,os,re,sqlite3,subprocess,sys
from pathlib import Path
import server as owner_dashboard
import customers
SCRIPTS=Path(__file__).resolve().parents[2]/'scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('support',SCRIPTS/'support-session.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
class Receiver(http.server.HTTPServer):
    def __init__(self,ip,port,host,context,db=owner_dashboard.db):
        super().__init__((ip,port),Handler);self.host_header=host+':'+str(self.server_port);self.context=context;self.db=db
    def get_request(self):
        sock,addr=super().get_request();sock.settimeout(5)
        try:return self.context.wrap_socket(sock,server_side=True),addr
        except BaseException:sock.close();raise
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status):
        body=b'{"ok":true}' if status==200 else b'{"ok":false}'
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):self.send(404)
    def do_POST(self):
        if self.headers.get_all('Host',[])!=[self.server.host_header] or self.path!='/v1/health' or self.headers.get('Origin') or self.headers.get('Transfer-Encoding') or self.headers.get_all('Content-Type',[])!=['application/json']:self.send(403);return
        auth=self.headers.get_all('Authorization',[]);lengths=self.headers.get_all('Content-Length',[])
        if len(auth)!=1 or not re.fullmatch(r'Bearer [A-Za-z0-9_-]{43}',auth[0]):self.send(401);return
        try:
            if len(lengths)!=1 or not 0<int(lengths[0])<=4096:raise ValueError()
            report=json.loads(self.rfile.read(int(lengths[0])))
            with self.server.db() as db:customers.receive(db,report,auth[0][7:])
        except (ValueError,KeyError,TypeError,sqlite3.Error,OSError):self.send(403);return
        self.send(200)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cert',required=True,type=Path);p.add_argument('--key',required=True,type=Path);p.add_argument('--port',type=int,default=17993);p.add_argument('--apply',action='store_true');a=p.parse_args()
    if os.geteuid()==0 or not 1024<=a.port<=65535 or a.port in (8790,8791):p.error('Non-root owner and separate private port required')
    host,ip=support.identity(json.loads(subprocess.check_output(['tailscale','status','--json'],text=True,timeout=15)))
    ctx=support.tls_context(a.cert.absolute(),a.key.absolute(),host)
    # The real owner registry only, never the demo database.
    if not (owner_dashboard.HOME/'cash.sqlite3').is_file():p.error('Initialize the real private business registry first')
    if not a.apply:print('Preview: private HTTPS write-only health receiver, port',a.port,'; review customer-specific ACL and no public forwarding before --apply');return
    os.umask(0o077)
    with Receiver(ip,a.port,host,ctx) as r:
        print('Private health receiver: https://'+r.host_header+'/v1/health',flush=True);r.serve_forever()
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Receiver unavailable: '+type(e).__name__)
