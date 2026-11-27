#!/usr/bin/env python3
"""Pair one trusted lab client to TLS-only routes after successful account setup."""
import ipaddress,json,os,pwd,re,subprocess,sys
from pathlib import Path
from account_progress import read
ROOT=Path(__file__).resolve().parents[1]
DIR=Path('/etc/jobbi/pilot-tls')
PORTS=(18080,18081,18082,18083,18085,18086,18087,18088,18090)
REQUIRED={'music','navidrome','movies','photos','files','passwords','tasks','monitor'}
def private_ip(s):
    ip=ipaddress.IPv4Address(s)
    if not any(ip in ipaddress.IPv4Network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):raise ValueError('Lab LAN only')
    return str(ip)
def config(addr,client,optional=()):
    addr,client=private_ip(addr),private_ip(client)
    if addr==client:raise ValueError('Pair a separate lab client')
    servers=[]
    if set(optional)-{'dns','invidious'}:raise ValueError('Unexpected optional route')
    extra=tuple(port for key,port in (('dns',18089),('invidious',18091)) if key in optional)
    for port in PORTS+extra:
        guard='location ~ ^/admin(?:/|$) { return 404; }' if port==18087 else ''
        servers.append(f'''server {{
 listen {addr}:{port} ssl;
 server_name {addr};
 ssl_certificate {DIR}/cert.pem;
 ssl_certificate_key {DIR}/key.pem;
 ssl_protocols TLSv1.2 TLSv1.3;
 allow {client};
 deny all;
 if ($host != "{addr}") {{ return 421; }}
 {guard}
 location / {{
  proxy_pass http://127.0.0.1:{port};
  proxy_http_version 1.1;
  proxy_set_header Host $http_host;
  proxy_set_header X-Forwarded-Host $http_host;
  proxy_set_header X-Forwarded-Proto https;
  proxy_set_header X-Forwarded-For $remote_addr;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection $connection_upgrade;
  proxy_buffering off;
  proxy_request_buffering off;
  proxy_read_timeout 3600s;
  client_max_body_size 0;
 }}
}}''')
    return 'user www-data;\nworker_processes 1;\npid /run/jobbi-pilot-nginx.pid;\nerror_log stderr warn;\nevents { worker_connections 512; }\nhttp {\n access_log off;\n map $http_upgrade $connection_upgrade { default upgrade; \'\' close; }\n'+'\n'.join(servers)+'\n}\n'
def main():
    if os.geteuid()!=0:raise ValueError('Root-managed lab gateway required')
    cfg=json.loads((DIR/'setup.json').read_text());i=Path(cfg['instance'])
    if i!=Path('/srv/jobbi-data/laptop-test'):raise ValueError('Unexpected pilot instance')
    marker=i/'.pilot-lan-client.json'
    if not marker.exists():return
    if marker.is_symlink():raise ValueError('Invalid pairing record')
    addr=private_ip(cfg['address']);client=private_ip(json.loads(marker.read_text())['client'])
    if ipaddress.IPv4Address(client) not in ipaddress.IPv4Network(cfg['network']):raise ValueError('Client not on approved local subnet')
    status=read(i)
    if set(status)!=REQUIRED or status.get('passwords')!='invited' or any(status[k]!='verified' for k in REQUIRED-{'passwords'}):raise ValueError('All core accounts must be verified and vault invited')
    user=pwd.getpwnam(cfg['operator'])
    if user.pw_uid!=1000:raise ValueError('Original pilot operator required')
    nginx=DIR/'nginx.conf';unit=Path('/etc/systemd/system/jobbi-pilot-gateway.service')
    if nginx.exists() or unit.exists():raise ValueError('Existing gateway configuration; review')
    from pilot_options import read as read_options
    optional={k for k,v in read_options(i).items() if k in ('dns','invidious') and v=='ready'}
    nginx.write_text(config(addr,client,optional));nginx.chmod(0o640)
    def run(*args):subprocess.run(args,check=True)
    origin=['runuser','-u',user.pw_name,'--',sys.executable,str(ROOT/'scripts/pilot-lan-origins.py'),str(i),addr]
    run('/usr/sbin/nginx','-t','-c',str(nginx))
    run(*origin)
    try:
        unit.write_text('[Unit]\nDescription=Jobbi paired-client lab TLS gateway\nAfter=network-online.target docker.service jobbi-laptop-test-boot-recover.service\nWants=network-online.target\nRequires=docker.service\n[Service]\nType=simple\nExecStart=/usr/sbin/nginx -c '+str(nginx)+' -g "daemon off;"\nExecReload=/bin/kill -HUP $MAINPID\nRestart=on-failure\n[Install]\nWantedBy=multi-user.target\n')
        run('systemctl','daemon-reload');run('systemctl','enable','--now','jobbi-pilot-gateway.service')
        if subprocess.run(['systemctl','is-active','--quiet','jobbi-pilot-gateway.service']).returncode:raise ValueError('Gateway not active')
    except BaseException:
        subprocess.run(['systemctl','disable','--now','jobbi-pilot-gateway.service'],check=False)
        run(*origin,'--rollback');raise
    print('Paired-client lab dashboard ready: https://'+addr+':18080/ ; verify fingerprint. No public access.',flush=True)
if __name__=='__main__':main()
