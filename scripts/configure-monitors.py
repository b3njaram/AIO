#!/usr/bin/env python3
"""Add missing fixed private application monitors, using customer-owned Kuma login."""
import argparse,getpass,json,os,re,sys,threading
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('app_manager',Path(__file__).with_name('app-manager.py'));app_manager=module_from_spec(spec);spec.loader.exec_module(app_manager)
TARGETS={'music':'http://jobbi-music:3131/api/status','navidrome':'http://navidrome:4533/','movies':'http://frontend/','photos':'http://immich-server:2283/','files':'http://nextcloud/status.php','passwords':'http://vaultwarden/alive','tasks':'http://vikunja:3456/api/v1/info','dns':'http://pihole/admin/'}
def targets(i):
    e=app_manager.identity(i)
    if 'monitor' not in e['COMPOSE_PROFILES'].split(',') or e['BIND_IP']!='127.0.0.1':raise ValueError('Local private Uptime Kuma required')
    apps={a['id'] for a in json.loads((i/'dashboard.json').read_text())['apps']}
    return e,{'dashboard':'http://dashboard:8080/healthz',**{k:v for k,v in TARGETS.items() if k in apps}}
def missing(desired,existing):
    urls={x.get('url') for x in existing.values() if isinstance(x,dict) and x.get('type')=='http'}
    return {k:v for k,v in desired.items() if v not in urls}
def configure(e,desired,user,pw,apply):
    import socketio
    c=socketio.Client(reconnection=False,request_timeout=15)
    arrived=threading.Event();seen={}
    @c.on('monitorList')
    def received(rows):
        if isinstance(rows,dict):seen.clear();seen.update(rows);arrived.set()
    try:
        c.connect('http://127.0.0.1:'+e['MONITOR_PORT'],transports=['polling'],wait_timeout=15)
        if not c.call('login',{'username':user,'password':pw},timeout=20).get('ok'):raise ValueError('Owner login rejected')
        arrived.clear()
        if not c.call('getMonitorList',timeout=20).get('ok') or not arrived.wait(10):raise ValueError('Cannot verify existing monitors')
        new=missing(desired,seen)
        if apply:
            for k,url in new.items():
                result=c.call('add',{'name':'Jobbi Home · '+k,'type':'http','url':url,'interval':60,'accepted_statuscodes':['200-399','401-403'],'notificationIDList':{},'active':True,'conditions':[],'kafkaProducerBrokers':[],'kafkaProducerSaslOptions':{},'rabbitmqNodes':[]},timeout=20)
                if not result.get('ok'):raise ValueError('Monitor creation refused; existing monitors untouched')
        return {'missing':sorted(new),'created':sorted(new) if apply else [],'scope':'HTTP reachability only, no application data or external notifications'}
    finally:
        if c.connected:c.disconnect()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--username',default='owner');p.add_argument('--apply',action='store_true');a=p.parse_args()
    e,desired=targets(a.instance.resolve())
    if not sys.stdin.isatty():p.error('Use a trusted terminal')
    pw=getpass.getpass('Customer Kuma password: ')
    print(json.dumps(configure(e,desired,a.username,pw,a.apply),indent=2))
if __name__=='__main__':
    try:main()
    except Exception as e:sys.exit('Monitor configuration stopped: '+type(e).__name__)
