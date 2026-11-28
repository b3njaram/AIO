#!/usr/bin/env python3
"""Generate a private, credential-free bilingual delivery and recovery guide."""
import argparse,json,os,re,sys
from pathlib import Path
from urllib.parse import urlsplit
def guide(config,release,lang):
    if lang not in ('en','es'):raise ValueError('Invalid language')
    es=lang=='es'
    tr=lambda a,b:b if es else a
    sha=release['aio_commit']
    if not re.fullmatch('[a-f0-9]{40}',sha):raise ValueError('Invalid release')
    titles={'music':'Jobbi Music','navidrome':'Navidrome','movies':'StreamHub','photos':'Immich','files':'Nextcloud','passwords':'Vaultwarden','tasks':'Vikunja','monitor':'Uptime Kuma','dns':'Pi-hole','remote':'Tailscale'}
    lines=['# JobbiSoft Home — '+tr('Customer guide','Guía del cliente'),'',
           tr('Draft for review — not a signed acceptance or warranty.','Borrador para revisión — no es aceptación ni garantía firmada.'),
           '','Release / Versión: '+sha,'','## '+tr('Your applications','Tus aplicaciones'),'']
    for app in config['apps']:
        id=app['id']
        if id not in titles:raise ValueError('Unknown app')
        url=app.get('url')
        if url:
            u=urlsplit(url)
            if u.scheme!='https' or not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+\.ts\.net',u.hostname or '') or u.username or u.password or u.query or u.fragment or u.path not in ('','/','/admin/') or u.port is not None and not 1<=u.port<=65535:
                raise ValueError('Review non-approved app origin before export')
            lines.append('- '+titles[id]+': '+url)
        else:lines.append('- '+titles[id]+': '+tr('Confirm private address with installer.','Confirma la dirección privada con el instalador.'))
    lines+=['','## '+tr('First day','Primer día'),'',
       '- '+tr('Use your own private network and accounts. Keep passwords and recovery keys in a separate secure place.','Usa tu propia red privada y cuentas. Guarda contraseñas y claves de recuperación por separado.'),
       '- '+tr('Open the dashboard, verify each selected app, and test access on your own phone or computer.','Abre el panel, verifica cada app y prueba el acceso en tu teléfono o computadora.'),
       '- '+tr('Only upload media and files you are authorized to use.','Sube únicamente contenido y archivos que tengas autorización para usar.'),
       '','## '+tr('Maintenance and recovery','Mantenimiento y recuperación'),'',
       '- '+tr('Review storage, drive health, backup dates, notifications and UPS status in Maintenance.','Revisa espacio, salud de discos, respaldos, avisos y UPS en Mantenimiento.'),
       '- '+tr('RAID is not a backup. Keep an independent encrypted copy and recovery key separately.','RAID no sustituye un respaldo. Conserva una copia cifrada independiente y su clave por separado.'),
       '- '+tr('If a disk disappears, do not format it or bypass storage protection. Contact your technician.','Si desaparece un disco, no lo formatees ni omitas la protección de almacenamiento. Contacta a tu técnico.'),
       '- '+tr('For recovery, verify backup checksums, restore exact images to a new stopped instance, then test it privately before changing access. Never overwrite the only copy.','Para recuperar, verifica las sumas de respaldo, restaura las imágenes exactas en una instancia nueva detenida y pruébala en privado antes de cambiar el acceso. Nunca sobrescribas la única copia.'),
       '- '+tr('Do not run simultaneous live copies or downgrade a migrated database. Reconcile changes before rollback.','No ejecutes dos copias activas ni regreses una base migrada. Reconcilia cambios antes de revertir.'),
       '','## '+tr('Support and privacy','Soporte y privacidad'),'',
       '- '+tr('Monitoring and temporary diagnostic access are optional and revocable. No permanent technician access is required.','El monitoreo y acceso temporal de diagnóstico son opcionales y revocables. No se exige acceso permanente del técnico.'),
       '- '+tr('Keep the agreed support dates, contact, hardware warranty, receipts and signed acceptance separately.','Conserva por separado fechas de soporte, contacto, garantía de hardware, recibos y aceptación firmada.'),
       '- '+tr('No mandatory recurring JobbiSoft subscription; third-party services or optional support may have their own costs and terms.','Sin suscripción periódica obligatoria de JobbiSoft; terceros o soporte opcional pueden tener sus propios costos y términos.'),
       '','## '+tr('Handoff checklist','Lista de entrega'),'']
    for en,sp in [('Customer-controlled accounts and private access','Cuentas y acceso privado del cliente'),('Selected apps tested on customer devices','Apps probadas en dispositivos del cliente'),('Independent backup and successful restore drill','Respaldo independiente y prueba de restauración'),('Hardware and power qualification','Validación del equipo y energía'),('Warranty, receipt and support agreement delivered','Garantía, recibo y acuerdo de soporte entregados'),('Temporary installer access removed','Acceso temporal del instalador eliminado')]:lines.append('- [ ] '+tr(en,sp))
    return '\n'.join(lines)+'\n'
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--lang',choices=['en','es'],default='en');a=p.parse_args();i=a.instance.resolve()
    config=json.loads((i/'dashboard.json').read_text());release=json.loads((i/'release.json').read_text())
    output=a.output.expanduser().absolute();root=Path(__file__).resolve().parents[1]
    if root in output.parent.resolve().parents or output.parent.resolve()==root or i==output.parent.resolve() or i in output.parent.resolve().parents:raise ValueError('Use private output outside repository and customer instance')
    os.umask(0o077)
    body=guide(config,release,a.lang)
    with output.open('x') as out:out.write(body)
    print('Private draft created; verify addresses and actual acceptance before delivery.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError) as e:sys.exit('Delivery guide refused: '+type(e).__name__)
