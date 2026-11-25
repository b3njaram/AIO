#!/usr/bin/env python3
"""Explicit customer-authorized export; never sends telemetry or includes credentials."""
import argparse,datetime as dt,json,math,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def report(i,id):
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}',id):raise ValueError('Invalid registry appliance ID')
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if env.get('INSTANCE_DIR')!=str(i):raise ValueError('Instance mismatch')
    src=i/'data/.dashboard-metrics/health.json'
    if src.is_symlink() or src.stat().st_size>65536:raise ValueError('Invalid health snapshot')
    s=json.loads(src.read_text());at=dt.datetime.fromisoformat(s['at']);now=dt.datetime.now(dt.timezone.utc)
    if at.tzinfo is None or not now-dt.timedelta(minutes=45)<=at<=now+dt.timedelta(minutes=1):raise ValueError('Refresh the local health snapshot first')
    release=json.loads((i/'release.json').read_text())['aio_commit']
    if not re.fullmatch('[a-f0-9]{40}',release):raise ValueError('Invalid release')
    def num(x,lo,hi):
        return x if type(x) in (float,int) and math.isfinite(x) and lo<=x<=hi else None
    temp=[num(x,-30,150) for x in s.get('temperature_c',[])]+[num(x.get('temperature_c'),-30,150) for x in s.get('drives',[])]
    temp=[x for x in temp if x is not None]
    def state(value,allowed,fallback):return value if value in allowed else fallback
    count=s.get('service_alert_count')
    return {'schema':1,'kind':'jobbi-health-share','appliance_id':id,'at':at.isoformat(),'release':release,'free_percent':num(s.get('data_free_percent'),0,100),'temperature_c':max(temp) if temp else None,'alerts':count if type(count) is int and 0<=count<=10000 else None,'backup':state(s.get('backup',{}).get('state'),('verified','stale','review','mount_unavailable','not_verified'),'not_verified'),'raid':state(s.get('storage',{}).get('redundancy',{}).get('state'),('healthy','degraded','syncing','review'),'unknown'),'updates':state(s.get('updates',{}).get('state'),('current','review_available','no_approved_release','not_checked'),'unknown')}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--appliance-id',required=True);p.add_argument('--output',type=Path);p.add_argument('--share',action='store_true',help='Customer explicitly approves this export');a=p.parse_args()
    r=report(a.instance.resolve(),a.appliance_id)
    if not a.share:print(json.dumps(r,indent=2));print('Preview only; nothing sent or saved.');return
    if not a.output:p.error('Provide a new private output file')
    out=a.output.expanduser().absolute()
    if ROOT==out.parent.resolve() or ROOT in out.parent.resolve().parents:p.error('Keep reports outside Git')
    os.umask(0o077)
    with out.open('x') as file:json.dump(r,file,indent=2)
    print('Private report saved. Customer chooses whether to send it to technician.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError) as e:sys.exit('Export refused: '+str(e))
