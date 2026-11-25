"""Private appliance registry; only explicitly shared, manually imported health reports."""
import datetime as dt,json,math,re
from operations import identifier,string
def schema(db):
    db.executescript("""CREATE TABLE IF NOT EXISTS appliances(
    id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id),
    label TEXT NOT NULL, consent INTEGER NOT NULL DEFAULT 0,
    consent_at TEXT, report TEXT, imported TEXT);
    CREATE TABLE IF NOT EXISTS appliance_events(
    id INTEGER PRIMARY KEY, appliance_id TEXT NOT NULL REFERENCES appliances(id),
    kind TEXT NOT NULL, recorded TEXT NOT NULL);""")
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
def rows(db):
    out=[]
    for row in db.execute('SELECT * FROM appliances ORDER BY label,id'):
        x=dict(row);x['consent']=bool(x['consent']);x['report']=json.loads(x['report']) if x['report'] and x['consent'] else None
        r=x['report'];x['state']='not_shared' if not x['consent'] else 'unknown'
        if r:
            age=now()-timestamp(r['at'])
            x['state']='stale' if age>dt.timedelta(hours=24) else 'review' if r['alerts'] is None or r['free_percent'] is None or r['alerts']>0 or r['free_percent']<15 or r['backup']!='verified' or r['raid'] in ('degraded','review','syncing') else 'reported_ok'
        out.append(x)
    return out
