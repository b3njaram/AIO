#!/usr/bin/env python3
"""Export only fixed appliance monitor summaries from the local Kuma SQLite DB."""
import argparse,datetime as dt,json,os,sqlite3,time
from pathlib import Path
from private_origins import atomic_write
IDS=('dashboard','music','navidrome','movies','photos','files','passwords','tasks','dns','invidious')
def summarize(db,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    result={'at':now.isoformat(),'state':'unavailable','monitors':{}}
    if not db.is_file() or db.is_symlink():return result
    cutoff=(now-dt.timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        deadline=time.monotonic()+5
        with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=2) as conn:
            conn.execute('PRAGMA query_only=ON')
            conn.execute('PRAGMA trusted_schema=OFF')
            conn.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
            for key in IDS:
                # Do not export arbitrary monitor names, URLs, headers, messages,
                # responses, secrets, custom monitors, or notification settings.
                rows=conn.execute('SELECT id,active FROM monitor WHERE name=? LIMIT 2',('Jobbi Home · '+key,)).fetchall()
                if len(rows)!=1:continue
                mid,active=rows[0]
                # Bounded recent samples, not a claim of time-weighted uptime.
                samples=conn.execute('SELECT status,ping FROM heartbeat WHERE monitor_id=? AND time>=? ORDER BY time DESC,id DESC LIMIT 10000',(mid,cutoff)).fetchall()
                counted=[x for x in samples if x[0] in (0,1)]
                pings=[x[1] for x in counted if x[0]==1 and isinstance(x[1],(int,float)) and 0<=x[1]<=600000]
                up=sum(x[0]==1 for x in counted)
                result['monitors'][key]={'state':'paused' if not active else {0:'down',1:'up',2:'pending',3:'maintenance'}.get(samples[0][0],'unknown') if samples else 'unknown',
                    'samples':len(counted),'success_percent':round(100*up/len(counted),2) if counted else None,
                    'avg_ms':round(sum(pings)/len(pings),1) if pings else None,
                    'recent':[x[0] for x in reversed(samples[:40]) if x[0] in (0,1,2,3)]}
        result['state']='available'
    except (sqlite3.Error,OSError,ValueError):
        result.update(state='unavailable',monitors={})
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);a=p.parse_args();i=a.instance.resolve()
    e=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if os.geteuid()==0 or e.get('OWNER_UID')!=str(os.getuid()) or e.get('INSTANCE_DIR')!=str(i):p.error('Original instance operator required')
    data=i/'data';out=data/'.dashboard-metrics';db=data/'uptime'/'kuma.db'
    if not out.is_dir() or any(x.is_symlink() for x in (data,out,db.parent,db)):p.error('Unsafe metrics or database path')
    payload=summarize(db)
    atomic_write(out/'monitoring.json',json.dumps(payload).encode(),0o644)
if __name__=='__main__':main()
