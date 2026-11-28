#!/usr/bin/env python3
"""Collect private appliance acceptance evidence; never claims physical tests it did not observe."""
import argparse,datetime as dt,hashlib,json,os,platform,re,subprocess,sys
from pathlib import Path
from backup_mount import mount_identity
from diagnostics import inspect
from restore import verified_archives
from storage_manager import snapshot as storage_snapshot
def boot_id():
    return hashlib.sha256(Path('/proc/sys/kernel/random/boot_id').read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def collect(instance,backup,devices=()):
    env=dict(x.split('=',1) for x in (instance/'.env').read_text().splitlines() if '=' in x)
    if env.get('INSTANCE_DIR')!=str(instance) or not re.fullmatch('jobbi-[a-z0-9-]+',env.get('COMPOSE_PROJECT_NAME','')):raise ValueError('Invalid instance')
    diag=inspect(instance,devices);release=read(instance/'release.json')
    configs=read(instance/'dashboard.json')
    state=read(instance/'onboarding.json') if (instance/'onboarding.json').is_file() else {}
    apps={a['id'] for a in configs['apps']}
    project=env['COMPOSE_PROJECT_NAME']
    backups=sorted(x for x in backup.glob(project+'-*') if re.fullmatch(re.escape(project)+r'-\d{8}T\d{6}Z',x.name) and x.is_dir() and not x.is_symlink() and (x/'SHA256SUMS').is_file())
    verified=None;backup_error='No completed backup'
    if instance.stat().st_dev==backup.stat().st_dev:backup_error='Not independent filesystem'
    elif backups:
        try:verified_archives(backups[-1]);verified=backups[-1].name;backup_error=None
        except (OSError,ValueError):backup_error='Checksum verification failed'
    guard=Path('/etc/systemd/system/docker.service.d/90-jobbi-storage.conf')
    return {'timestamp':dt.datetime.now(dt.timezone.utc).isoformat(),'release':release['aio_commit'],'architecture':platform.machine(),'os':platform.freedesktop_os_release().get('PRETTY_NAME'),'boot':boot_id(),'data_mount':mount_identity(instance),'backup_mount':mount_identity(backup),'storage':storage_snapshot(instance),'services':diag['services'],'boot_guard_present':guard.is_file() and not guard.is_symlink(),'verified_backup':verified,'backup_error':backup_error,'selected_apps':sorted(apps),'operator_confirmed_apps':sorted(apps&set(state)),'health':{'data_free_percent':diag['data_free_percent'],'docker_free_percent':diag['docker_free_percent'],'ram_gib':diag['ram_gib'],'temperatures':diag['thermal_zones'],'drive_health':[{'state':x['state'],'temperature_c':x.get('temperature_c')} for x in diag['smart']] if isinstance(diag['smart'],list) else [],'alerts':diag['alerts']},'manual_required':['Exact hardware SKU, bays, power supply, cooling and actual drive identities','Disk and RAID layout and independent physical failure domain','Measured wall watts idle and streaming/indexing','Measured temperatures and performance under actual load','Second-device private TLS and ACL denial; no public access','Restore to independent storage and verify all selected app data','Physical reboot and missing-disk recovery','Supported phone/TV clients and signed customer acceptance']}
def compare(before,after):
    return {'different_boot':before['boot']!=after['boot'],'same_release':before['release']==after['release'],'same_data_mount':before['data_mount']==after['data_mount'],'same_backup_mount':before['backup_mount']==after['backup_mount'],'post_boot_alerts':after['health']['alerts'],'note':'Observed software and mount evidence only; physical and functional checks still require technician evidence.'}
def acceptance(report):
    checks = {
        'cpu_architecture': 'pass' if report['architecture'] == 'x86_64' else 'fail',
        'backup_archive_integrity': 'pass' if report['verified_backup'] else 'fail',
        'independent_restore': 'not-tested',
        'application_login': 'not-tested',
        'private_network_access': 'not-tested',
        'service_restart_recovery': 'not-tested',
    }
    for item in report['services']:
        name = item['Service']
        if item['State'] != 'running' or item['Health'] == 'unhealthy':
            status = 'fail'
        elif item['Health'] == 'healthy':
            status = 'pass'
        else:
            status = 'not-tested'
        checks['container_health/' + name] = status
    return checks

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('backup',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--before',type=Path);p.add_argument('--smart-device',action='append',default=[]);a=p.parse_args()
    i=a.instance.resolve();b=a.backup.resolve();out=a.output.expanduser().resolve();repo=Path(__file__).resolve().parents[1]
    if out.exists() or out==repo or repo in out.parents:raise ValueError('Write a fresh private report outside Git')
    if not b.is_dir():raise ValueError('Mount independent backup before qualification')
    result=collect(i,b,a.smart_device)
    result["checks"] = acceptance(result)
    if a.before:result['reboot_comparison']=compare(read(a.before),result)
    os.umask(0o077);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(result,f,indent=2)
    print('Private evidence report:',out)
    print('Not a release certificate. Complete each manual acceptance check on actual hardware.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Qualification stopped: '+str(e))
