#!/usr/bin/env python3
"""Private single-operator dashboard. Loopback only; use an SSH tunnel."""
import argparse,base64,csv,datetime as dt,hashlib,hmac,http.server,json,os,re,secrets,sqlite3,subprocess,sys,tempfile,threading
from pathlib import Path
from decimal import Decimal
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'business'),str(ROOT/'business/sourcing')]
import records,order
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
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status,data,mime='application/json; charset=utf-8'):
        if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        if status==401:self.send_header('WWW-Authenticate','Basic realm="Jobbi private business"')
        for k,v in {'Content-Type':mime,'Content-Length':str(len(data)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; img-src https://i.ebayimg.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(data)
    def auth(self):
        host=self.headers.get('Host','')
        if host not in ('localhost:'+str(self.server.server_port),'127.0.0.1:'+str(self.server.server_port)):
            self.send(403,{'error':'Use localhost via SSH tunnel'});return False
        expected='Basic '+base64.b64encode(('owner:'+self.server.password).encode()).decode()
        if not hmac.compare_digest(self.headers.get('Authorization',''),expected):
            self.send(401,{'error':'Authentication required'});return False
        return True
    def do_GET(self):
        if not self.auth():return
        u=urlsplit(self.path);q=parse_qs(u.query)
        try:
            if u.path in ('/','/app.js','/style.css'):
                name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[u.path]
                self.send(200,(Path(__file__).parent/name).read_bytes(),{'/':'text/html; charset=utf-8','/app.js':'application/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[u.path]);return
            if u.path=='/api/init':data={'profiles':PROFILES,'suppliers':sourcing.CAT['suppliers'],'reports':report_ids()}
            elif u.path=='/api/job':
                with LOCK:data={**JOB,'reports':report_ids()}
            elif u.path=='/api/report':data=read_report(q.get('id',[''])[0])
            elif u.path=='/api/links':
                profile=q.get('profile',['family'])[0]
                if profile not in PROFILES:raise ValueError('Invalid profile')
                data=supplier_links(profile)
            elif u.path=='/api/orders':data=list_orders()
            else:self.send(404,{'error':'Not found'});return
            self.send(200,data)
        except (ValueError,KeyError,TypeError,OSError,sqlite3.Error):self.send(400,{'error':'Unable to read requested data'})
    def do_POST(self):
        if not self.auth():return
        # Same-origin JSON only; no CORS and no cross-site form requests.
        if self.headers.get('X-Jobbi-Request')!='1' or self.headers.get('Origin') not in ('http://localhost:'+str(self.server.server_port),'http://127.0.0.1:'+str(self.server.server_port)) or self.headers.get('Content-Type','').split(';')[0]!='application/json':
            self.send(403,{'error':'Same-origin request required'});return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=65536:raise ValueError('Invalid request size')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('Invalid payload')
            routes={'/api/search':start_search,'/api/cost':costing,'/api/confirmed':confirmations,'/api/confirm':lambda d:confirmations(d,save=True),'/api/remove-offer':lambda d:confirmations(d,remove=True),'/api/order':lambda d:save_order(d,True),'/api/order-update':lambda d:save_order(d,False),'/api/payment':payment}
            fn=routes.get(self.path)
            if fn is None:self.send(404,{'error':'Not found'});return
            self.send(200,fn(data))
        except (ValueError,KeyError,TypeError,ArithmeticError,argparse.ArgumentTypeError,sqlite3.IntegrityError) as e:self.send(400,{'error':str(e)[:300]})
        except (OSError,sqlite3.Error):self.send(500,{'error':'Local storage operation failed'})
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8790);p.add_argument('--init',action='store_true');a=p.parse_args()
    if not 1024<=a.port<=65535:p.error('Invalid port')
    os.umask(0o077);HOME.mkdir(parents=True,exist_ok=True);CONFIG.mkdir(parents=True,exist_ok=True)
    token=CONFIG/'dashboard-password'
    if a.init:
        if not token.exists():
            fd=os.open(token,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as stream:stream.write(secrets.token_urlsafe(32)+'\n')
        print('Dashboard credentials file:',private_file(token));return
    password=private_file(token).read_text().strip()
    if len(password)<32:p.error('Invalid dashboard password')
    with db():pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',a.port),Handler);server.password=password
    print('Private dashboard on http://127.0.0.1:'+str(a.port),flush=True);server.serve_forever()
if __name__=='__main__':main()
