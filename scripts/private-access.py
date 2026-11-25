#!/usr/bin/env python3
"""Plan private customer Tailscale HTTPS. Does not change tailnet or execute Serve."""
import argparse,fcntl,ipaddress,json,re,shlex,subprocess,sys
from pathlib import Path
from private_origins import prepare,rollback
ROOT=Path(__file__).resolve().parents[1]
APP_PORTS={'dashboard':'DASH_PORT','music':'MUSIC_PORT','navidrome':'NAV_PORT','movies':'MOVIE_PORT','photos':'PHOTO_PORT','files':'CLOUD_PORT','passwords':'VAULT_PORT','tasks':'TASK_PORT','monitor':'MONITOR_PORT'}
def output(*args):
    return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=15)
def hostname(raw):
    host=str(raw).rstrip('.').lower()
    if len(host)>253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){2,}[a-z]{2,}',host) or not host.endswith('.ts.net'):
        raise ValueError('A customer-owned MagicDNS .ts.net name is required')
    return host
def routes(env,config,host,base):
    host=hostname(host)
    if not 1024<=base<=65525:raise ValueError('Use a dedicated HTTPS base port between 1024 and 65525')
    if env.get('BIND_IP')!='127.0.0.1':raise ValueError('Use loopback-only application bindings')
    selected={'dashboard'}|{a['id'] for a in config['apps']}
    if 'dns' in selected:raise ValueError('DNS requires a separate private LAN design; not routed here')
    result={}
    for offset,(app,key) in enumerate(APP_PORTS.items()):
        if app not in selected:continue
        port=int(env[key])
        if not 1024<=port<=65535:raise ValueError('Invalid backend port')
        https=base+offset
        result[app]={'port':https,'target':'http://127.0.0.1:'+str(port),'url':'https://'+host+':'+str(https)}
    if len({x['target'] for x in result.values()})!=len(result):raise ValueError('Duplicate backend ports')
    if any(x['port']==int(y['target'].rsplit(':',1)[1]) for x in result.values() for y in result.values()):raise ValueError('HTTPS and backend port ranges must be disjoint')
    return result
def existing_conflicts(status,ports):
    if status is None:status={}
    if not isinstance(status,dict):raise ValueError('Unrecognized Serve status')
    allowed={'TCP','Web','AllowFunnel','Foreground','Services','ETag'}
    if set(status)-allowed:raise ValueError('Unrecognized Serve status fields; inspect manually')
    # Only allow a dedicated host with no existing Serve/Funnel rules.
    if any(status.get(k) for k in ('TCP','Web','AllowFunnel','Foreground','Services')):
        raise ValueError('Existing Serve/Funnel configuration found; use a dedicated customer host or review manually. No reset is performed.')
def verify_config(status,planned,host):
    if not isinstance(status,dict):raise ValueError('Unrecognized Serve status')
    if set(status)-{'TCP','Web','AllowFunnel','Foreground','Services','ETag'}:
        raise ValueError('Unrecognized Serve status fields')
    if status.get('Foreground') or status.get('Services'):
        raise ValueError('Unexpected additional Serve configuration')
    if any(status.get('AllowFunnel',{}).values()):raise ValueError('Public Funnel is enabled; stop and review')
    expected_tcp={str(r['port']):{'HTTPS':True} for r in planned.values()}
    expected_web={host+':'+str(r['port']):{'Handlers':{'/':{'Proxy':r['target']}}} for r in planned.values()}
    if status.get('TCP')!=expected_tcp or status.get('Web')!=expected_web:
        raise ValueError('Actual Serve listeners or handlers differ from the private access plan')
    return True
def commands(planned):
    return {'enable':[shlex.join(['sudo','tailscale','serve','--bg','--https='+str(r['port']),r['target']]) for r in planned.values()],
      'disable':[shlex.join(['sudo','tailscale','serve','--https='+str(r['port']),'off']) for r in planned.values()]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--https-base',type=int,default=19443);p.add_argument('--verify',action='store_true',help='Read-only verify actual Serve config after enabling')
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--prepare-origins',action='store_true',help='Save previous settings and write proposed origins on this customer host')
    mode.add_argument('--rollback-origins',action='store_true',help='Restore saved settings after disabling all Serve routes')
    a=p.parse_args()
    if a.verify and (a.prepare_origins or a.rollback_origins):p.error('Choose one operation')
    i=a.instance.resolve();env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if env.get('INSTANCE_DIR')!=str(i) or not re.fullmatch(r'jobbi-[a-z0-9-]+',env.get('COMPOSE_PROJECT_NAME','')):p.error('Invalid customer instance')
    lock=None
    if a.prepare_origins or a.rollback_origins:
        lock=(i/'.private-origins.lock').open('a')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if a.rollback_origins:
        existing_conflicts(json.loads(output('tailscale','serve','status','--json')),set())
        rollback(i)
        print('Previous files restored. Recreate the dashboard and affected services on this instance.')
        return
    config=json.loads((i/'dashboard.json').read_text())
    state=json.loads(output('tailscale','status','--json'))
    if state.get('BackendState')!='Running':p.error('Customer must enroll this device in their own tailnet first')
    host=hostname(state['Self']['DNSName'])
    plan=routes(env,config,host,a.https_base)
    # Manual onboarding confirmations must exist before even generating exposure instructions.
    selected={x['id'] for x in config['apps']}-{'remote','passwords'}
    onboard=i/'onboarding.json'
    done=json.loads(onboard.read_text()) if onboard.is_file() else {}
    if not selected<=set(done):p.error('Complete local setup and mark all selected applications except remote and Vaultwarden (which needs HTTPS) first')
    status=json.loads(output('tailscale','serve','status','--json'))
    if a.verify:
        verify_config(status,plan,host)
        print(json.dumps({'verified_serve_config':True,'urls':{k:v['url'] for k,v in plan.items()},'note':'Configuration check only. Verify TLS and app login from customer device, ACL denial from unauthorized account, and no public access.'},indent=2));return
    existing_conflicts(status,{x['port'] for x in plan.values()})
    c=commands(plan)
    # Output configuration proposals, never copy customer secrets or rewrite instance files.
    cfg={**config,'apps':[{**app,**({'url':plan[app['id']]['url']} if app['id'] in plan else {})} for app in config['apps']]}
    changes={}
    if 'music' in plan:changes['MUSIC_HTTPS']='true'
    if 'passwords' in plan:changes['VAULT_DOMAIN']=plan['passwords']['url']
    if 'tasks' in plan:changes.update(TASK_URL=plan['tasks']['url']+'/',TASK_REGISTRATION='false')
    if a.prepare_origins:
        prepare(i,cfg,changes)
        print('Saved previous configuration and prepared private origins. Recreate dashboard and affected services before enabling Serve.')
    print(json.dumps({'host':host,'routes':plan,'proposed_env_changes':changes,'proposed_dashboard_config':cfg,'enable_commands':c['enable'],'disable_commands':c['disable'],'note':'Preview only. Confirm Vaultwarden signups are closed and the intended owner invitation before serving; finish its acceptance after HTTPS. Configure app origins and verify ACLs before enabling routes. Never enable Funnel. Do not run on owner infrastructure.'},indent=2))
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as e:sys.exit('Private access plan stopped: '+str(e))
