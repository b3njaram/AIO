"""Journal and reconcile the dedicated customer host's Tailscale Serve bindings."""
import json
import subprocess
from pathlib import Path
from private_origins import atomic_write


def serve_status():
    raw=subprocess.check_output(['tailscale','serve','status','--json'],text=True,timeout=15)
    return json.loads(raw) or {}


def verify_backends(instance, plan):
    ctl=['bash',str(Path(__file__).with_name('ctl.sh')),str(instance)]
    ids=subprocess.check_output([*ctl,'ps','-q'],text=True).split()
    if not ids:
        raise ValueError('No running customer containers')
    ports={}
    running=set()
    for cid in ids:
        # Read only runtime bindings, service label, and the three nonsecret
        # security settings. Never print the container environment.
        obj=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
        service=obj['Config']['Labels']['com.docker.compose.service']
        running.add(service)
        env=dict(x.split('=',1) for x in obj['Config']['Env'] or [] if '=' in x)
        required={
            'backend':{'JOBBI_PRIVATE_HTTPS':'true'},
            'jobbi-music':{'PUBLIC_HTTPS':'true','ENABLE_ACCOUNT_MANAGEMENT':'false'},
            'vaultwarden':{'SIGNUPS_ALLOWED':'false','DOMAIN':plan.get('passwords',{}).get('url')},
            'vikunja':{'VIKUNJA_SERVICE_ENABLEREGISTRATION':'false','VIKUNJA_SERVICE_PUBLICURL':plan.get('tasks',{}).get('url','')+'/'}
        }.get(service,{})
        if any(env.get(k)!=v for k,v in required.items()):
            raise ValueError('Recreate and verify private settings for '+service)
        if obj['HostConfig']['NetworkMode']=='host':
            raise ValueError('Host networking requires manual review')
        for bindings in (obj['NetworkSettings']['Ports'] or {}).values():
            for bind in bindings or []:
                if bind['HostIp']!='127.0.0.1':
                    raise ValueError('Customer port is published outside loopback')
                ports[int(bind['HostPort'])]=service
    if 'movies' in plan and 'backend' not in running:
        raise ValueError('Missing StreamHub backend')
    owners={'dashboard':'dashboard','music':'jobbi-music','navidrome':'navidrome','movies':'frontend','photos':'immich-server','files':'nextcloud','passwords':'vaultwarden','tasks':'vikunja','monitor':'uptime-kuma'}
    for app,row in plan.items():
        if ports.get(int(row['target'].rsplit(':',1)[1]))!=owners[app]:
            raise ValueError('Missing running customer backend for '+app)


def manage(instance, plan, host, disable, verify, empty):
    journal=instance/'.private-serve.json'
    if disable:
        recorded=json.loads(journal.read_text())
        if recorded['host']!=host or recorded['instance']!=str(instance):
            raise ValueError('Serve journal belongs to a different host or instance')
        plan=recorded['routes']
    else:
        empty(serve_status(),set())
        verify_backends(instance,plan)
        if journal.exists():
            raise ValueError('Previous Serve transaction exists. Review or roll back.')
        atomic_write(journal,json.dumps({'instance':str(instance),'host':host,'routes':plan}).encode(),0o600)

    def active():
        status=serve_status()
        tcp=status.get('TCP') or {}
        present={app:r for app,r in plan.items() if str(r['port']) in tcp}
        if present:
            verify(status,present,host)
        else:
            empty(status,set())
        return present

    if disable:
        for app in reversed(plan):
            if app in active():
                subprocess.run(['tailscale','serve','--https='+str(plan[app]['port']),'off'],check=True,timeout=60)
        empty(serve_status(),set())
        journal.unlink()
        return
    for app,row in plan.items():
        active()
        subprocess.run(['tailscale','serve','--bg','--https='+str(row['port']),row['target']],check=True,timeout=60)
        if app not in active():
            raise ValueError('Serve did not install expected route. Use --rollback-routes.')
    verify(serve_status(),plan,host)
