#!/usr/bin/env python3
"""Private single-operator dashboard. Loopback only; private Serve or SSH."""
import argparse,base64,csv,datetime as dt,hashlib,hmac,http.server,json,os,re,secrets,sqlite3,subprocess,sys,tempfile,threading
from pathlib import Path
from decimal import Decimal
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'business'),str(ROOT/'business/sourcing')]
import records,order
import operations as ops
import search as sourcing
from retailers import links
HOME=Path.home()/'.local/share/jobbi-business'
REPORTS=HOME/'sourcing'
CONFIG=Path.home()/'.config/jobbi-business'
JOB={'state':'idle','message':''}
LOCK=threading.Lock()
PROFILES=sourcing.CAT['profiles']
MARKETS=sourcing.MARKETS
ID_RE=r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}'
REPORT_RE=r'(?:core|family|family8|plus)-\d{8}T\d{12}Z'
def private_file(p):
    if not p.is_file() or p.stat().st_mode&0o077:raise ValueError('Missing or insecure private file')
    return p
def db():
    d=records.open_db(HOME/'cash.sqlite3')
    d.row_factory=sqlite3.Row
    d.executescript("""CREATE TABLE IF NOT EXISTS order_details(order_id TEXT PRIMARY KEY REFERENCES orders(id), label TEXT NOT NULL, stage TEXT NOT NULL, delivered TEXT, months INTEGER NOT NULL, hardware_condition TEXT NOT NULL, note TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS confirmed_offers(profile TEXT NOT NULL,target TEXT NOT NULL,part TEXT NOT NULL,url TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(profile,target,part,url));""")
    ops.schema(d)
    return d
def validate_id(v):
    if not isinstance(v,str) or not re.fullmatch(ID_RE,v):raise ValueError('Invalid order or transaction ID')
    return v
def txt(v,maxlen=200):
    if not isinstance(v,str) or len(v)>maxlen:raise ValueError('Invalid text field')
    return v.strip()
def money(v):
    x=sourcing.dec(v)
    if x is None:raise ValueError('Enter finite nonnegative amounts')
    return x
def options(d):
    profile=d.get('profile','family');target=d.get('target','MX')
    if profile not in PROFILES or target not in MARKETS:raise ValueError('Invalid profile or market')
    return profile,target
def report_ids():
    if not REPORTS.exists():return []
    return sorted((p.name for p in REPORTS.iterdir() if re.fullmatch(REPORT_RE,p.name) and p.is_dir() and not p.is_symlink() and (p/'offers.json').is_file()),key=lambda x:x.split('-',1)[1],reverse=True)[:100]
def read_report(rid):
    if not re.fullmatch(REPORT_RE,rid) or rid not in report_ids():raise ValueError('Report not found')
    p=REPORTS/rid/'offers.json'
    if p.is_symlink() or p.stat().st_size>20_000_000:raise ValueError('Invalid report')
    d=json.loads(p.read_text())
    return {k:d.get(k,[]) for k in ('offers','coverage','bom')}
def start_search(d):
    profile,target=options(d);markets=d.get('markets','both')
    if markets not in ('US','MX','both'):raise ValueError('Invalid markets')
    with LOCK:
        if JOB['state']=='running':raise ValueError('A search is already running')
        JOB.update(state='running',message='Searching with DealCompare…')
    def worker():
        try:
            p=subprocess.run([sys.executable,str(ROOT/'business/sourcing/search.py'),'--profile',profile,'--target',target,'--markets',markets],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=240)
            with LOCK:JOB.update(state='done' if p.returncode==0 else 'error',message='Search completed; check coverage and results.' if p.returncode==0 else 'Search failed. Run the CLI for diagnostics.')
        except (OSError,subprocess.TimeoutExpired):
            with LOCK:JOB.update(state='error',message='Search timed out or failed.')
    threading.Thread(target=worker,daemon=True).start()
    return {'ok':True}
def supplier_links(profile):
    out=[]
    for m,sellers in sourcing.CAT['suppliers'].items():
        for name,domain in sellers.items():
            for p in PROFILES[profile]['parts']:
                for q in p.get('queries') or p.get('models') or [p['query']]:
                    direct,indexed=links(m,name,q,domain)
                    out.append({'market':m,'supplier':name,'part':p['id'],'query':q,'url':direct,'indexed':indexed})
    return out
def checked_rows(rows,profile,target,fx):
    fields=(ROOT/'business/sourcing/verified.example.csv').read_text().strip().split(',')
    with tempfile.NamedTemporaryFile(mode='w',dir=HOME,suffix='.csv',newline='',encoding='utf-8') as tmp:
        w=csv.DictWriter(tmp,fieldnames=fields);w.writeheader();w.writerows(rows);tmp.flush()
        return sourcing.import_verified(tmp.name,PROFILES[profile]['parts'],target,fx)
def confirmations(d,save=False,remove=False):
    profile,target=options(d);fx=money(d['fx']) if d.get('fx') not in ('',None) else None
    if fx is not None and fx<=0:raise ValueError('FX must be positive')
    with db() as conn:
        if save:
            raw=d.get('offer',{});fields=(ROOT/'business/sourcing/verified.example.csv').read_text().strip().split(',')
            row={k:txt(raw.get(k,''),1200) for k in fields}
            row['confirmed']='yes' if raw.get('confirmed')=='yes' else 'no'
            if row['confirmed']!='yes':raise ValueError('Explicit verification required')
            if not checked_rows([row],profile,target,fx):raise ValueError('Offer not confirmed')
            conn.execute('INSERT OR REPLACE INTO confirmed_offers VALUES(?,?,?,?,?)',(profile,target,row['part'],row['url'],json.dumps(row)))
        if remove:
            conn.execute('DELETE FROM confirmed_offers WHERE profile=? AND target=? AND part=? AND url=?',(profile,target,txt(d.get('part','')),txt(d.get('url',''),1200)))
        rawrows=[json.loads(x[0]) for x in conn.execute('SELECT payload FROM confirmed_offers WHERE profile=? AND target=?',(profile,target))]
    valid=[];excluded=[]
    for row in rawrows:
        try:valid.extend(checked_rows([row],profile,target,fx))
        except (ValueError,KeyError,TypeError,ArithmeticError) as e:excluded.append({'url':row['url'],'reason':str(e)})
    bom=sourcing.choose(PROFILES[profile]['parts'],valid)
    return {'saved':rawrows,'verified':valid,'excluded':excluded,'bom':bom,'total':str(sum(Decimal(x['landed']) for x in bom)) if bom else None,'currency':MARKETS[target][0]}
def costing(d):
    m=d.get('market')
    if m not in order.MARKETS:raise ValueError('Invalid market')
    cur,setup,renewal=order.MARKETS[m]
    values=[money(d.get(k)) for k in ('hardware','labor','support','shipping','warranty','overhead')]
    hardware,*costs=values
    result=order.calculate(hardware,setup,renewal,int(d.get('months',6)),money(d.get('markup',12)),*costs,Decimal(0),money(d.get('floor',20)))
    return dict(currency=cur,**dict(zip(('price','cost','fees','contribution','margin','minimum'),map(str,result))))
def plus_months(day,months):
    import calendar
    index=day.month-1+months;y=day.year+index//12;m=index%12+1
    return dt.date(y,m,min(day.day,calendar.monthrange(y,m)[1]))
def list_orders():
    with db() as conn:
        out=[]
        for r in conn.execute('SELECT o.*,d.label,d.stage,d.delivered,d.months,d.hardware_condition,d.note FROM orders o LEFT JOIN order_details d ON d.order_id=o.id ORDER BY opened DESC,id DESC'):
            x=dict(r);_,_,paid=records.balance(conn,x['id']);x['paid']=paid;x['due']=x['total']-paid
            x['support_end']=x['warranty_end']=x['installation_warranty_end']=None
            if x['delivered']:
                day=dt.date.fromisoformat(x['delivered'])
                x['support_end']=plus_months(day,x['months']).isoformat()
                x['installation_warranty_end']=(day+dt.timedelta(days=90)).isoformat()
                if x['hardware_condition']=='new':x['warranty_end']=plus_months(day,12).isoformat()
                elif x['hardware_condition']=='refurbished':x['warranty_end']=(day+dt.timedelta(days=90)).isoformat()
            x['transactions']=[dict(y) for y in conn.execute('SELECT id,kind,amount,recorded FROM cash WHERE order_id=? ORDER BY recorded,rowid',(x['id'],))]
            x['components']=[dict(y) for y in conn.execute('SELECT component,provider,expires FROM component_warranties WHERE order_id=? ORDER BY expires,component',(x['id'],))]
            x['installation_events']=[dict(y) for y in conn.execute('SELECT step,result,note,recorded FROM installation_events WHERE order_id=? ORDER BY id DESC',(x['id'],))]
            out.append(x)
        return out
def save_order(d,new):
    id=validate_id(d.get('id'));stage=d.get('stage','quoted');months=int(d.get('months',6));condition=d.get('hardware_condition','customer')
    if stage not in ('quoted','accepted','procurement','installing','delivered','cancelled') or months not in (6,12) or condition not in ('new','refurbished','customer'):raise ValueError('Invalid order details')
    delivered=d.get('delivered') or None
    if delivered:delivered=dt.date.fromisoformat(delivered).isoformat()
    if stage=='delivered' and not delivered:raise ValueError('Delivery date required')
    if delivered and delivered>dt.date.today().isoformat():raise ValueError('Delivery date cannot be future')
    label=txt(d.get('label',''));note=txt(d.get('note',''),2000)
    with db() as conn:
        if new:
            if d.get('market') not in MARKETS:raise ValueError('Invalid market')
            total=records.cents(str(d.get('total')))
            conn.execute('INSERT INTO orders VALUES(?,?,?,?)',(id,d['market'],total,dt.date.today().isoformat()))
        else:records.balance(conn,id)
        conn.execute('INSERT OR REPLACE INTO order_details VALUES(?,?,?,?,?,?,?)',(id,label,stage,delivered,months,condition,note))
    return {'ok':True}
def payment(d):
    id=validate_id(d.get('id'));txn=validate_id(d.get('transaction'));kind=d.get('kind')
    if kind not in records.KINDS:raise ValueError('Invalid cash transaction')
    date=dt.date.fromisoformat(d.get('date') or dt.date.today().isoformat())
    if date>dt.date.today():raise ValueError('Transaction cannot be future')
    with db() as conn:records.add_payment(conn,txn,id,kind,records.cents(str(d.get('amount'))),date.isoformat())
    return {'ok':True}
def operations(d,action):
    with db() as conn:
        if action=='component':
            ops.warranty(conn,d);return {'ok':True}
        if action=='installation-event':
            ops.installation_event(conn,d);return {'ok':True}
        if action=='case':
            ops.save_case(conn,d);return {'ok':True}
        if action=='plan':
            p=ops.plan(d)
            if d.get('order_id'):
                i=validate_id(d['order_id']);records.balance(conn,i)
                conn.execute('INSERT OR REPLACE INTO install_plans VALUES(?,?)',(i,json.dumps(p)))
            return p
        if action in ('handoff','document'):
            i=validate_id(d.get('order_id'))
            o=next((x for x in list_orders() if x['id']==i),None)
            if o is None:raise ValueError('Order not found')
            row=conn.execute('SELECT payload FROM install_plans WHERE order_id=?',(i,)).fetchone()
            if action=='document':
                from customer_documents import render
                pdf=render(o,json.loads(row[0]) if row else None,d.get('kind'),d.get('lang'),d.get('transaction'),ops.handoff)
                return {'pdf':base64.b64encode(pdf).decode('ascii')}
            return {'text':ops.handoff(o,json.loads(row[0]) if row else None,d.get('lang','en'))}
    raise ValueError('Invalid operation')
def permitted_origins(port, extra=()):
    """Explicit browser origins for a loopback-only private reverse proxy.
    Never trust forwarded host or origin headers.
    """
    origins={f'http://localhost:{port}',f'http://127.0.0.1:{port}'}
    for value in extra:
        u=urlsplit(value)
        host=u.hostname or ''
        if (u.scheme not in ('http','https') or not host or u.username is not None
                or u.password is not None or u.path or u.query or u.fragment
                or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*',host)
                or not ('.' not in host or host.endswith('.ts.net'))
                or u.netloc != host+((':'+str(u.port)) if u.port is not None else '')
                or (u.port is not None and not 1<=u.port<=65535)
                or value != u.scheme+'://'+u.netloc
                or (u.port == (80 if u.scheme=='http' else 443))):
            raise ValueError('Use an exact private hostname origin, e.g. http://macmini2012:8791 or https://device.tailnet.ts.net (no path or default port)')
        origins.add(value)
    return {urlsplit(o).netloc: {x for x in origins if urlsplit(x).netloc==urlsplit(o).netloc} for o in origins}

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status,data,mime='application/json; charset=utf-8'):
        if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        if status==401:self.send_header('WWW-Authenticate','Basic realm="Jobbi private business"')
        for k,v in {'Content-Type':mime,'Content-Length':str(len(data)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; img-src https://i.ebayimg.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(data)
    def auth(self):
        hosts=self.headers.get_all('Host',[])
        if len(hosts)!=1 or hosts[0] not in self.server.allowed_origins:
            self.send(403,{'error':'Unapproved private dashboard hostname'});return False
        if self.server.preview:return True
        expected='Basic '+base64.b64encode(('owner:'+self.server.password).encode()).decode()
        if not hmac.compare_digest(self.headers.get('Authorization',''),expected):
            self.send(401,{'error':'Authentication required'});return False
        return True
    def do_GET(self):
        if not self.auth():return
        u=urlsplit(self.path);q=parse_qs(u.query)
        try:
            if u.path in ('/','/app.js','/language.js','/style.css'):
                name={'/':'index.html','/language.js':'language.js','/app.js':'app.js','/style.css':'style.css'}[u.path]
                self.send(200,(Path(__file__).parent/name).read_bytes(),{'/':'text/html; charset=utf-8','/language.js':'application/javascript; charset=utf-8','/app.js':'application/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[u.path]);return
            if u.path=='/api/init':data={'profiles':PROFILES,'suppliers':sourcing.CAT['suppliers'],'reports':report_ids(),'preview':self.server.preview}
            elif u.path=='/api/job':
                with LOCK:data={**JOB,'reports':report_ids()}
            elif u.path=='/api/report':data=read_report(q.get('id',[''])[0])
            elif u.path=='/api/links':
                profile=q.get('profile',['family'])[0]
                if profile not in PROFILES:raise ValueError('Invalid profile')
                data=supplier_links(profile)
            elif u.path=='/api/orders':data=list_orders()
            elif u.path=='/api/cases':
                with db() as conn:data=ops.cases(conn)
            elif u.path=='/api/plans':
                with db() as conn:data=[{'order_id':r[0],'plan':json.loads(r[1])} for r in conn.execute('SELECT order_id,payload FROM install_plans')]
            else:self.send(404,{'error':'Not found'});return
            self.send(200,data)
        except (ValueError,KeyError,TypeError,OSError,sqlite3.Error):self.send(400,{'error':'Unable to read requested data'})
    def do_POST(self):
        if not self.auth():return
        # Same-origin JSON only; no CORS and no cross-site form requests.
        if self.headers.get('X-Jobbi-Request')!='1' or len(self.headers.get_all('Origin',[]))!=1 or self.headers.get('Origin') not in self.server.allowed_origins[self.headers['Host']] or self.headers.get('Content-Type','').split(';')[0]!='application/json':
            self.send(403,{'error':'Same-origin request required'});return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=65536:raise ValueError('Invalid request size')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('Invalid payload')
            routes={'/api/search':start_search,'/api/cost':costing,'/api/confirmed':confirmations,'/api/confirm':lambda d:confirmations(d,save=True),'/api/remove-offer':lambda d:confirmations(d,remove=True),'/api/order':lambda d:save_order(d,True),'/api/order-update':lambda d:save_order(d,False),'/api/payment':payment,'/api/plan':lambda d:operations(d,'plan'),'/api/case':lambda d:operations(d,'case'),'/api/component':lambda d:operations(d,'component'),'/api/installation-event':lambda d:operations(d,'installation-event'),'/api/handoff':lambda d:operations(d,'handoff'),'/api/document':lambda d:operations(d,'document')}
            if self.server.preview and self.path=='/api/search':
                self.send(403,{'error':'Live hardware search is disabled in the no-login demo.'});return
            fn=routes.get(self.path)
            if fn is None:self.send(404,{'error':'Not found'});return
            self.send(200,fn(data))
        except (ValueError,KeyError,TypeError,ArithmeticError,argparse.ArgumentTypeError,sqlite3.IntegrityError) as e:self.send(400,{'error':str(e)[:300]})
        except (OSError,sqlite3.Error):self.send(500,{'error':'Local storage operation failed'})
def main():
    global HOME,REPORTS,CONFIG
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8790);p.add_argument('--init',action='store_true');p.add_argument('--allow-origin',action='append',default=[],help='Exact private Tailscale browser origin; repeat for additional names');p.add_argument('--preview-no-auth',action='store_true',help='Port 8791 only; separate demo database, no live sourcing, no password');p.add_argument('--container-preview',action='store_true',help='Demo container only: publish through a host loopback mapping');a=p.parse_args()
    if a.container_preview and (not a.preview_no_auth or a.port!=8791 or not Path('/.dockerenv').exists()):p.error('Container listener requires the isolated no-login Docker demo')
    if not 1024<=a.port<=65535:p.error('Invalid port')
    try:allowed=permitted_origins(a.port,a.allow_origin)
    except ValueError as e:p.error(str(e))
    os.umask(0o077)
    if a.preview_no_auth:
        if a.port!=8791 or a.init:p.error('No-login demo is limited to port 8791; do not use --init')
        demo=Path.home()/'.jobbi-no-login-demo'
        for directory in (demo,demo/'sourcing',demo/'config'):
            if directory.is_symlink():p.error('Demo directory must not be a symlink')
            directory.mkdir(mode=0o700,exist_ok=True)
            if not directory.is_dir() or directory.stat().st_uid!=os.getuid() or directory.stat().st_mode&0o077:p.error('Demo directory must be privately owned')
        for name in ('cash.sqlite3','cash.sqlite3-wal','cash.sqlite3-shm','cash.sqlite3-journal'):
            path=demo/name
            if path.is_symlink() or path.exists() and (not path.is_file() or path.stat().st_nlink!=1):p.error('Unsafe demo database path')
        HOME=demo;REPORTS=demo/'sourcing';CONFIG=demo/'config'
    HOME.mkdir(parents=True,exist_ok=True);CONFIG.mkdir(parents=True,exist_ok=True)
    token=CONFIG/'dashboard-password'
    if a.init:
        if not token.exists():
            fd=os.open(token,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as stream:stream.write(secrets.token_urlsafe(32)+'\n')
        print('Dashboard credentials file:',private_file(token));return
    password=None if a.preview_no_auth else private_file(token).read_text().strip()
    if not a.preview_no_auth and len(password)<32:p.error('Invalid dashboard password')
    with db():pass
    server=http.server.ThreadingHTTPServer(('0.0.0.0' if a.container_preview else '127.0.0.1',a.port),Handler);server.password=password;server.allowed_origins=allowed;server.preview=a.preview_no_auth
    if a.preview_no_auth:print('NO-LOGIN DEMO: use synthetic records only; restrict Serve to your devices.',flush=True)
    print('Private dashboard on http://127.0.0.1:'+str(a.port),flush=True);server.serve_forever()
if __name__=='__main__':main()
