"""Private customer operations; generate plans, never execute customer-host commands."""
import datetime as dt,json,re,shlex
from pathlib import PurePosixPath
APPS={'music':'Jobbi Music / Navidrome','movies':'StreamHub','photos':'Immich','files':'Nextcloud','passwords':'Vaultwarden','tasks':'Vikunja','monitor':'Uptime Kuma','remote':'Tailscale','dns':'Pi-hole'}
PORTS={'music':1,'movies':3,'photos':5,'files':6,'passwords':7,'tasks':8,'monitor':10,'dns':9}
def string(x,limit=1000):
    if not isinstance(x,str) or len(x)>limit:raise ValueError('Invalid text')
    return x.strip()
def identifier(x):
    x=string(x,64)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',x):raise ValueError('Invalid identifier')
    return x
def path(x):
    x=string(x,240)
    if not re.fullmatch(r'/[A-Za-z0-9_.\/-]+',x) or '..' in PurePosixPath(x).parts or x=='/':raise ValueError('Use an absolute mounted path without spaces')
    return str(PurePosixPath(x))
def schema(conn):
    conn.executescript("""CREATE TABLE IF NOT EXISTS support_cases(
    id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id), category TEXT NOT NULL, subject TEXT NOT NULL,
    status TEXT NOT NULL, note TEXT NOT NULL, opened TEXT NOT NULL, updated TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS install_plans(order_id TEXT PRIMARY KEY REFERENCES orders(id), payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS component_warranties(
        order_id TEXT NOT NULL REFERENCES orders(id), component TEXT NOT NULL, provider TEXT NOT NULL,
        expires TEXT NOT NULL, PRIMARY KEY(order_id,component));
    CREATE TABLE IF NOT EXISTS installation_events(
        id INTEGER PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id),
        step TEXT NOT NULL, result TEXT NOT NULL, note TEXT NOT NULL, recorded TEXT NOT NULL);""")
def warranty(conn,d):
    order=identifier(d.get('order_id'))
    component=string(d.get('component'),120)
    provider=string(d.get('provider'),120)
    if not component or not provider:raise ValueError('Component and warranty provider required')
    expires=dt.date.fromisoformat(d['expires']).isoformat()
    conn.execute("""INSERT INTO component_warranties VALUES(?,?,?,?) ON CONFLICT(order_id,component)
        DO UPDATE SET provider=excluded.provider,expires=excluded.expires""",(order,component,provider,expires))

def installation_event(conn,d):
    order=identifier(d.get('order_id'))
    step=d.get('step')
    result=d.get('result')
    if step not in ('hardware','storage','accounts','https','backup','handoff') or result not in ('passed','blocked','pending'):
        raise ValueError('Choose an installation step and result')
    note=string(d.get('note',''),500)
    if result=='blocked' and not note:raise ValueError('Describe the installation blocker')
    conn.execute('INSERT INTO installation_events(order_id,step,result,note,recorded) VALUES(?,?,?,?,?)',
                 (order,step,result,note,dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')))

def plan(d):
    name=string(d.get('name',''),36)
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,35}',name):raise ValueError('Use a lowercase customer instance name')
    root=path(d.get('root',''));backup=path(d.get('backup',''))
    if root==backup or PurePosixPath(root) in PurePosixPath(backup).parents or PurePosixPath(backup) in PurePosixPath(root).parents:raise ValueError('Separate data and backup paths required')
    apps=d.get('apps')
    if not isinstance(apps,list) or not apps or any(not isinstance(x,str) or x not in APPS for x in apps):raise ValueError('Select supported applications')
    if 'dns' in apps:raise ValueError('Pi-hole requires a separate customer-approved LAN setup; not included in loopback wizard')
    apps=list(dict.fromkeys(apps))
    port=int(d.get('port',18080));tb=int(d.get('tb',4));ram=int(d.get('ram',16))
    if not 1024<=port<=65525 or not 1<=tb<=40 or ram not in (8,16,32):raise ValueError('Invalid port, storage or RAM')
    tz=string(d.get('tz','America/Ciudad_Juarez'),80)
    if tz not in ('America/Ciudad_Juarez','America/Denver','Etc/UTC'):raise ValueError('Choose supported time zone')
    p={'name':name,'root':root,'backup':backup,'apps':apps,'port':port,'tb':tb,'ram':ram,'tz':tz,'mirror':d.get('mirror') is True}
    instance=root+'/'+name
    # The target is not the dashboard host. Operator reviews and executes locally.
    def cmd(*a):return shlex.join(a)
    p['commands']='\n'.join(['# Run ONLY on a dedicated customer Linux host, from the reviewed AIO checkout.',
       '# Verify actual mounts, hardware, disk health, backup drive and free ports first.',
       cmd('python3','scripts/preflight.py','--data-root',root,'--backup-root',backup,'--apps',','.join(apps),'--minimum-free-gib',str(max(50,int(tb*1000**4/1024**3)))),
       '# Continue only if preflight passes and capacity/RAID are confirmed.',
       cmd('python3','scripts/install.py','--name',name,'--data-root',root,'--base-port',str(port),'--apps',','.join(apps),'--tz',tz),
       cmd('bash','scripts/verify.sh',instance),cmd('python3','scripts/onboard.py',instance),
       cmd('python3','scripts/diagnostics.py',instance), '# After account setup and customer consent for downtime:',
       cmd('python3','scripts/maintenance.py',instance,backup,'--run-backup')])
    p['note']='Loopback only. Confirm requested capacity, RAM and mirroring physically; no disks are formatted. Customer creates accounts and enables private HTTPS/remote access. Commands are not executed by the dashboard.'
    return p
def cases(conn):
    return [dict(x) for x in conn.execute('SELECT * FROM support_cases ORDER BY updated DESC,id DESC')]
def save_case(conn,d):
    i=identifier(d.get('id',''));o=identifier(d.get('order_id',''))
    category=d.get('category');status=d.get('status')
    if category not in ('support','warranty','return','maintenance') or status not in ('open','waiting','resolved'):raise ValueError('Invalid case type/status')
    subject=string(d.get('subject',''),200);note=string(d.get('note',''),2000)
    if not subject:raise ValueError('Subject required')
    today=dt.date.today().isoformat()
    old=conn.execute('SELECT order_id FROM support_cases WHERE id=?',(i,)).fetchone()
    if old and old[0]!=o:raise ValueError('Existing case cannot change order')
    conn.execute("""INSERT INTO support_cases VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET category=excluded.category,subject=excluded.subject,status=excluded.status,note=excluded.note,updated=excluded.updated""",(i,o,category,subject,status,note,today,today))
def handoff(order,plan,lang):
    if lang not in ('en','es'):raise ValueError('Invalid language')
    es=lang=='es';cur='MXN' if order['market']=='MX' else 'USD'
    heading='Entrega de Jobbi Home' if es else 'Jobbi Home handoff'
    lines=[heading,'='*len(heading),f"{'Folio' if es else 'Order'}: {order['id']}",f"{'Fecha de entrega' if es else 'Delivery date'}: {order['delivered'] or 'Pending / Pendiente'}",f"{'Total acordado' if es else 'Agreed total'}: {cur} {order['total']/100:.2f}",f"{'Efectivo neto recibido' if es else 'Net cash received'}: {cur} {order['paid']/100:.2f}",f"{'Fin de soporte' if es else 'Support ends'}: {order['support_end'] or 'Pending / Pendiente'}",f"{'Garantía de instalación' if es else 'Installation warranty ends'}: {order['installation_warranty_end'] or 'Pending / Pendiente'}",f"{'Garantía indicativa de equipo' if es else 'Indicative hardware warranty'}: {order['warranty_end'] or 'See item terms / Ver términos por equipo'}",'']
    if plan:
        lines += [f"{'Configuración solicitada' if es else 'Requested configuration'}: {plan['tb']} TB, {plan['ram']} GB RAM",('Espejo solicitado' if es else 'Mirror requested')+': '+('Sí / Yes' if plan['mirror'] else 'No'),('Aplicaciones' if es else 'Applications')+': '+', '.join(APPS[a] for a in plan['apps']),'']
    lines += (['Confirma capacidad y aplicaciones instaladas antes de entregar. Direcciones HTTPS privadas y credenciales se entregan por separado. No incluye contraseñas.','Usa el panel de tu servidor y clientes compatibles. Conserva un respaldo independiente; RAID no es respaldo.','Soporte: b3njaram06@gmail.com. Indica folio y descripción; no envíes contraseñas.','Sin mensualidad obligatoria. Mantenimiento opcional. Adjuntar garantía escrita por componente, aceptación y condiciones legales vigentes.','Este documento no es factura ni confirma pruebas pendientes.'] if es else ['Confirm actual installed capacity and applications before delivery. Private HTTPS addresses and credentials are handed over separately. No passwords included.','Use your server dashboard and compatible clients. Keep an independent backup; RAID is not a backup.','Support: b3njaram06@gmail.com. Include order ID and symptom; never send passwords.','No mandatory monthly fee. Optional maintenance. Attach written item-specific warranty, acceptance and applicable legal terms.','This document is not an invoice or proof of uncompleted acceptance tests.'])
    return '\n'.join(lines)+'\n'
