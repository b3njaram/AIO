"""Private appliance registry; only explicitly shared, manually imported health reports."""
import datetime as dt,json,math,re,hashlib,hmac,secrets
from operations import identifier,string
def schema(db):
    db.executescript("""CREATE TABLE IF NOT EXISTS appliances(
    id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id),
    label TEXT NOT NULL, consent INTEGER NOT NULL DEFAULT 0,
    consent_at TEXT, report TEXT, imported TEXT);
    CREATE TABLE IF NOT EXISTS appliance_events(
    id INTEGER PRIMARY KEY, appliance_id TEXT NOT NULL REFERENCES appliances(id),
    kind TEXT NOT NULL, recorded TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS appliance_reporting(appliance_id TEXT PRIMARY KEY REFERENCES appliances(id),token_hash TEXT NOT NULL,expires TEXT NOT NULL);""")
def now():return dt.datetime.now(dt.timezone.utc)
def event(db,id,kind):db.execute('INSERT INTO appliance_events(appliance_id,kind,recorded) VALUES(?,?,?)',(id,kind,now().isoformat()))
def save(db,d):
    id=identifier(d['id']);order=identifier(d['order_id']);label=string(d['label'],120)
    if not label:raise ValueError('Appliance label required')
    if not db.execute('SELECT 1 FROM orders WHERE id=?',(order,)).fetchone():raise ValueError('Unknown order')
    old=db.execute('SELECT order_id FROM appliances WHERE id=?',(id,)).fetchone()
    if old:
        if old[0]!=order:raise ValueError('Appliance is linked to another order')
        db.execute('UPDATE appliances SET label=? WHERE id=?',(label,id))
    else:
        db.execute('INSERT INTO appliances(id,order_id,label) VALUES(?,?,?)',(id,order,label));event(db,id,'registered')
    return {'ok':True}
def consent(db,d):
    id=identifier(d['id']);allow=d['allow']
    if type(allow) is not bool or d.get('confirmed') is not True:raise ValueError('Explicit customer consent or revocation required')
    if not db.execute('SELECT 1 FROM appliances WHERE id=?',(id,)).fetchone():raise ValueError('Unknown appliance')
    db.execute('UPDATE appliances SET consent=?,consent_at=?,report=NULL,imported=NULL WHERE id=?',(int(allow),now().isoformat(),id))
    db.execute('DELETE FROM appliance_reporting WHERE appliance_id=?',(id,))
    event(db,id,'sharing_allowed' if allow else 'sharing_revoked')
    return {'ok':True}
STATES={'backup':{'verified','stale','review','mount_unavailable','not_verified'},'raid':{'healthy','degraded','syncing','review','unknown'},'updates':{'current','review_available','no_approved_release','not_checked','unknown'}}
def timestamp(value):
    t=dt.datetime.fromisoformat(value)
    if t.tzinfo is None:raise ValueError('Timezone required')
    return t.astimezone(dt.timezone.utc)
def validate(report,id):
    keys={'schema','kind','appliance_id','at','release','free_percent','temperature_c','alerts','backup','raid','updates'}
    if not isinstance(report,dict) or set(report)!=keys or type(report['schema']) is not int or report['schema']!=1 or report['kind']!='jobbi-health-share' or report['appliance_id']!=id:raise ValueError('Invalid health report or appliance identity')
    if not isinstance(report['release'],str) or not re.fullmatch('[a-f0-9]{40}',report['release']):raise ValueError('Invalid release identity')
    t=timestamp(report['at'])
    if t>now()+dt.timedelta(minutes=2) or t<now()-dt.timedelta(days=7):raise ValueError('Report expired or timestamp in future')
    for key,low,high in [('free_percent',0,100),('temperature_c',-30,150),('alerts',0,10000)]:
        v=report[key]
        if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or not low<=v<=high):raise ValueError('Invalid health reading')
    if report['alerts'] is not None and type(report['alerts']) is not int:raise ValueError('Invalid alert count')
    if any(report[k] not in states for k,states in STATES.items()):raise ValueError('Invalid health state')
    return report
def ingest(db,d):
    id=identifier(d['id']);row=db.execute('SELECT consent,consent_at,report FROM appliances WHERE id=?',(id,)).fetchone()
    if not row or not row[0]:raise ValueError('Customer sharing is not enabled')
    r=validate(d['report'],id)
    t=timestamp(r['at'])
    if t<timestamp(row[1]):raise ValueError('Report predates current sharing consent')
    if row[2] and t<=timestamp(json.loads(row[2])['at']):raise ValueError('Report is older than or equal to last import')
    db.execute('UPDATE appliances SET report=?,imported=? WHERE id=?',(json.dumps(r),now().isoformat(),id));event(db,id,'report_imported')
    return {'ok':True}
def support_snapshot(db, data):
    appliance = identifier(data['id'])
    row = db.execute('SELECT report FROM appliances WHERE id=? AND consent=1', (appliance,)).fetchone()
    if not row or not row[0]:
        raise ValueError('No shared health report available')
    report = validate(json.loads(row[0]), appliance)
    fields = ('at', 'release', 'free_percent', 'temperature_c', 'alerts', 'backup', 'raid', 'updates')
    event(db, appliance, 'diagnostics_exported')
    return {'schema': 1, 'kind': 'jobbi-support-snapshot',
            'measurements': {key: report[key] for key in fields}}

def enable_reporting(db,d):
    id=identifier(d['id'])
    if d.get('confirmed') is not True:raise ValueError('Explicit customer approval required')
    row=db.execute('SELECT consent FROM appliances WHERE id=?',(id,)).fetchone()
    if not row or not row[0]:raise ValueError('Customer sharing must be enabled first')
    token=secrets.token_urlsafe(32);expires=(now()+dt.timedelta(days=90)).isoformat()
    db.execute('INSERT OR REPLACE INTO appliance_reporting(appliance_id,token_hash,expires) VALUES(?,?,?)',(id,hashlib.sha256(token.encode()).hexdigest(),expires))
    event(db,id,'reporting_enabled')
    return {'token':token,'expires':expires}
def disable_reporting(db,d):
    id=identifier(d['id'])
    if d.get('confirmed') is not True:raise ValueError('Confirm revocation')
    db.execute('DELETE FROM appliance_reporting WHERE appliance_id=?',(id,))
    event(db,id,'reporting_revoked')
    return {'ok':True}
def receive(db,report,token):
    if not isinstance(report,dict) or not isinstance(token,str) or not re.fullmatch('[A-Za-z0-9_-]{43}',token):raise ValueError('Invalid authorization')
    id=identifier(report.get('appliance_id'))
    # Serialize credential checking and ingestion with consent revocation.
    db.execute('BEGIN IMMEDIATE')
    row=db.execute('SELECT token_hash,expires FROM appliance_reporting WHERE appliance_id=?',(id,)).fetchone()
    if not row or timestamp(row[1])<=now() or not hmac.compare_digest(row[0],hashlib.sha256(token.encode()).hexdigest()):raise ValueError('Invalid authorization')
    r=validate(report,id)
    if now()-timestamp(r['at'])>dt.timedelta(minutes=45):raise ValueError('Report is stale')
    latest=db.execute('SELECT imported FROM appliances WHERE id=?',(id,)).fetchone()
    if latest and latest[0] and now()-timestamp(latest[0])<dt.timedelta(minutes=5):raise ValueError('Report interval too short')
    ingest(db,{'id':id,'report':r})
    return {'ok':True}
def rows(db):
    out=[]
    for row in db.execute('SELECT * FROM appliances ORDER BY label,id'):
        x=dict(row);x['consent']=bool(x['consent']);x['report']=json.loads(x['report']) if x['report'] and x['consent'] else None
        grant=db.execute('SELECT expires FROM appliance_reporting WHERE appliance_id=?',(x['id'],)).fetchone()
        x['reporting_expires']=grant[0] if grant and x['consent'] else None
        x['reporting']=bool(x['reporting_expires'] and timestamp(x['reporting_expires'])>now())
        r=x['report'];x['state']='not_shared' if not x['consent'] else 'unknown'
        if r:
            age=now()-timestamp(r['at'])
            x['state']='stale' if age>dt.timedelta(hours=1 if x['reporting'] else 24) else 'review' if r['alerts'] is None or r['free_percent'] is None or r['alerts']>0 or r['free_percent']<15 or r['backup']!='verified' or r['raid'] in ('degraded','review','syncing') else 'reported_ok'
        x['activity']=[dict(e) for e in db.execute('SELECT kind,recorded FROM appliance_events WHERE appliance_id=? ORDER BY id DESC LIMIT 12',(x['id'],))]
        out.append(x)
    return out
