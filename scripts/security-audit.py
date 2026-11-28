#!/usr/bin/env python3
"""Read-only exact-instance runtime safety checks. Never print container env or secrets."""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROFILES={
    'music':{'navidrome','jobbi-music','jobbi-social-db','jobbi-storage-agent'},
    'movies':{'prowlarr','torrserver','backend','frontend'},
    'photos':{'immich-server','immich-machine-learning','immich-redis','immich-db'},
    'files':{'nextcloud','nextcloud-db'},'passwords':{'vaultwarden'},
    'tasks':{'vikunja','vikunja-db'},'monitor':{'uptime-kuma'},'dns':{'pihole'}}
PUBLISHED={'dashboard':{'8080/tcp':'DASH_PORT'},'navidrome':{'4533/tcp':'NAV_PORT'},
    'jobbi-music':{'3131/tcp':'MUSIC_PORT'},'prowlarr':{'9696/tcp':'PROWLARR_PORT'},
    'frontend':{'80/tcp':'MOVIE_PORT'},'immich-server':{'2283/tcp':'PHOTO_PORT'},
    'nextcloud':{'80/tcp':'CLOUD_PORT'},'vaultwarden':{'80/tcp':'VAULT_PORT'},
    'vikunja':{'3456/tcp':'TASK_PORT'},'uptime-kuma':{'3001/tcp':'MONITOR_PORT'},
    'pihole':{'80/tcp':'DNS_WEB_PORT','53/tcp':'DNS_LISTEN_PORT','53/udp':'DNS_LISTEN_PORT'}}
HARDENED={'dashboard','jobbi-music','jobbi-storage-agent'}
def output(*args):return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=30)
def inspect(*args):return json.loads(output('docker','inspect',*args))
def expected_services(env):
    profiles=set(filter(None,env['COMPOSE_PROFILES'].split(',')))
    if profiles-set(PROFILES):raise ValueError('Unknown profile')
    return {'dashboard'}.union(*(PROFILES[p] for p in profiles))
def findings(instance,env,containers,networks):
    project=env['COMPOSE_PROJECT_NAME'];issues=[];seen=set();ids={c['Id'] for c in containers}
    def flag(service,reason):issues.append({'service':service,'check':reason})
    if env['BIND_IP']!='127.0.0.1':flag('instance','not_loopback_only')
    if env.get('TASK_REGISTRATION')!='false':flag('instance','task_registration_not_disabled')
    for c in containers:
        cfg=c['Config'];labels=cfg.get('Labels') or {};host=c['HostConfig'];net=c['NetworkSettings']
        service=labels.get('com.docker.compose.service','unknown')
        if service not in expected_services(env):flag('instance','unexpected_service');continue
        if labels.get('com.docker.compose.project')!=project or service in seen:flag(service,'project_or_duplicate_service')
        seen.add(service)
        if not c['State']['Running']:flag(service,'not_running')
        if host.get('Privileged') or host.get('PidMode')=='host' or host.get('IpcMode')=='host' or host.get('NetworkMode')=='host':flag(service,'host_privilege_or_namespace')
        if host.get('Devices') or host.get('DeviceRequests') or host.get('CapAdd'):flag(service,'unreviewed_device_or_capability')
        if host.get('RestartPolicy',{}).get('Name')!='unless-stopped':flag(service,'restart_policy')
        if service in HARDENED and (not host.get('ReadonlyRootfs') or 'ALL' not in (host.get('CapDrop') or []) or not any(x.startswith('no-new-privileges') for x in (host.get('SecurityOpt') or []))):flag(service,'hardening_missing')
        actual={(port,x['HostIp'],x['HostPort']) for port,bindings in (host.get('PortBindings') or {}).items() for x in bindings or []}
        intended={(port,'127.0.0.1',env[key]) for port,key in PUBLISHED.get(service,{}).items()}
        if actual!=intended:flag(service,'published_port_mismatch')
        runtime={(port,x['HostIp'],x['HostPort']) for port,bindings in (net.get('Ports') or {}).items() for x in bindings or []}
        if runtime!=intended:flag(service,'runtime_port_mismatch')
        links=set((net.get('Networks') or {}).keys())
        if service=='jobbi-storage-agent':
            if host.get('NetworkMode')!='none' or links-{'none'}:flag(service,'storage_agent_network')
        elif links!={project+'_default'}:flag(service,'unexpected_network')
        for mount in c.get('Mounts',[]):
            src=Path(mount['Source']);dest=mount['Destination']
            if dest in ('/var/run/docker.sock','/run/docker.sock') or src.name in ('docker.sock','containerd.sock'):flag(service,'engine_socket_mount');continue
            if mount['Type']=='bind':
                if src==Path('/etc/localtime') and not mount['RW']:continue
                # A lexical check alone is insufficient for symlinked host paths.
                if instance not in src.resolve().parents:flag(service,'bind_outside_instance')
            elif mount['Type']=='volume':
                if not mount.get('Name','').startswith(project+'_'):flag(service,'foreign_volume')
            else:flag(service,'unexpected_mount_type')
        values=dict(x.split('=',1) for x in cfg.get('Env') or [] if '=' in x)
        required={'jobbi-music':{'ENABLE_ACCOUNT_MANAGEMENT':'false','PUBLIC_HTTPS':env['MUSIC_HTTPS'],'DOWNLOADER_URL':'','SLSKD_URL':'','INVIDIOUS_URL':'disabled','INVIDIOUS_BACKUPS':''},
            'backend':{'JOBBI_PRIVATE_HTTPS':env['MOVIE_HTTPS']},
            'vaultwarden':{'SIGNUPS_ALLOWED':'false','DOMAIN':env['VAULT_DOMAIN']},
            'vikunja':{'VIKUNJA_SERVICE_ENABLEREGISTRATION':'false','VIKUNJA_SERVICE_PUBLICURL':env['TASK_URL']}}.get(service,{})
        if any(values.get(k)!=v for k,v in required.items()):flag(service,'security_setting_mismatch')
    if seen!=expected_services(env):flag('instance','missing_expected_services')
    if len(networks)!=1:flag('instance','project_network_count')
    for n in networks:
        if n.get('Name')!=project+'_default' or (n.get('Labels') or {}).get('com.docker.compose.project')!=project or set((n.get('Containers') or {}).keys())!=ids-{c['Id'] for c in containers if c['Config']['Labels'].get('com.docker.compose.service')=='jobbi-storage-agent'}:flag('instance','network_membership_mismatch')
    return issues
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);a=p.parse_args();i=a.instance.resolve()
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    project=env.get('COMPOSE_PROJECT_NAME','')
    if env.get('INSTANCE_DIR')!=str(i) or not re.fullmatch('jobbi-[a-z0-9-]+',project):raise ValueError('Invalid instance')
    issues=[]
    if (i/'.env').is_symlink() or (i/'.env').stat().st_mode&0o077:issues.append({'service':'instance','check':'credential_file_permissions'})
    ids=output('docker','ps','-aq','--filter','label=com.docker.compose.project='+project).split()
    networks=output('docker','network','ls','-q','--filter','label=com.docker.compose.project='+project).split()
    issues+=findings(i,env,inspect(*ids) if ids else [],inspect(*networks) if networks else [])
    print(json.dumps({'schema':1,'status':'review' if issues else 'passed','checks':issues,'scope':'loopback container isolation only; not external TLS or CVE certification'},indent=2))
    return bool(issues)
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as e:sys.exit('Security audit unavailable: '+type(e).__name__)
