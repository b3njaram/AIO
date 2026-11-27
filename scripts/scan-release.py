#!/usr/bin/env python3
"""Scan exact local container image IDs with a separately verified Trivy installation."""
import argparse,datetime as dt,importlib.util,json,os,re,shutil,subprocess,sys,tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('inventory',Path(__file__).with_name('release-inventory.py'))
inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
def summarize(data):
    if not isinstance(data,dict) or not isinstance(data.get('Results'),list) or not data['Results']:raise ValueError('No scanner result sections; cannot certify coverage')
    findings=set();licenses=set();evidence=[]
    for section in data['Results']:
        for v in section.get('Vulnerabilities') or []:
            severity=v.get('Severity','UNKNOWN').upper()
            evidence.append({'id':v.get('VulnerabilityID'), 'package':v.get('PkgName'),
                'installed':v.get('InstalledVersion'), 'fixed':v.get('FixedVersion') or None,
                'severity':severity,'target':section.get('Target'),'ecosystem':section.get('Type'),
                'status':v.get('Status'),'advisory':v.get('PrimaryURL'),
                'package_path':v.get('PkgPath'),'package_identifier':v.get('PkgIdentifier'),'package_id':v.get('PkgID'),
                'vendor':v.get('DataSource'),'references':v.get('References') or []})
            findings.add((v.get('VulnerabilityID','unknown'),v.get('PkgName','unknown'),v.get('InstalledVersion',''),v.get('FixedVersion',''),severity))
        for license in section.get('Licenses') or []:
            name=license.get('Name')
            if isinstance(name,str) and len(name)<200:licenses.add(name)
    return {'vulnerabilities':[dict(zip(('id','package','installed','fixed','severity'),x)) for x in sorted(findings)],'license_names':sorted(licenses),'sections':len(data['Results']),'advisories':evidence}
def scan(instance,scanner,destination):
    i=instance.resolve();out=destination.expanduser().absolute()
    if out.exists() or out.is_symlink() or not out.parent.is_dir():raise ValueError('Use new report directory')
    if i==out or i in out.parents:raise ValueError('Keep security scan evidence outside customer data')
    state=inventory.collect(i);release=json.loads((i/'release.json').read_text())
    os.umask(0o077);out.mkdir(mode=0o700)
    version=subprocess.check_output([scanner,'--version'],text=True,timeout=30)
    groups={}
    for name,row in state['services'].items():groups.setdefault(row['id'],[]).append(name)
    reports=[]
    for image,services in sorted(groups.items()):
        with tempfile.TemporaryDirectory(prefix='jobbi-scan-') as tmp:
            raw=Path(tmp)/'scan.json'
            cmd=[scanner,'image','--image-src','docker','--scanners','vuln,license','--list-all-pkgs','--format','json','--output',str(raw),'--timeout','15m',image]
            # Do not ignore unfixed findings or use an unreviewed ignore file in the repo.
            subprocess.run(cmd,cwd=tmp,check=True,timeout=950)
            result=summarize(json.loads(raw.read_text()))
            sbom=image.removeprefix('sha256:')+'.cdx.json'
            subprocess.run([scanner,'convert','--format','cyclonedx','--output',str(out/sbom),str(raw)],check=True,timeout=180)
            if not json.loads((out/sbom).read_text()).get('components'):
                raise ValueError('Scanner produced no SBOM components')
            result['sbom']=sbom
        reports.append({'image':image,'services':sorted(services),**result})
        print('Scanned',','.join(sorted(services)),':',len(result['vulnerabilities']),'findings across all severities',flush=True)
    payload={'schema':1,'at':dt.datetime.now(dt.timezone.utc).isoformat(),'release':release['aio_commit'],'scanner':version.strip(),'images':reports,'policy':'All vulnerability findings require release review; license discovery is not a compliance determination.'}
    # Provide a package-level action list without removing any gated findings.
    actions={}
    for report in reports:
        for v in report['vulnerabilities']:
            key=(v['package'],v['installed'],v['fixed'],v['severity'])
            row=actions.setdefault(key,{'package':key[0],'installed':key[1],'fixed':key[2],'severity':key[3],'ids':set(),'services':set()})
            row['ids'].add(v['id']);row['services'].update(report['services'])
    queue=[{**row,'ids':sorted(row['ids']),'services':sorted(row['services'])} for row in actions.values()]
    queue.sort(key=lambda x:(not bool(x['fixed']),{'CRITICAL':0,'HIGH':1,'UNKNOWN':2,'MEDIUM':3,'LOW':4}.get(x['severity'],5),-len(x['ids']),x['package']))
    (out/'remediation.json').write_text(json.dumps({'release':release['aio_commit'],'packages':queue},indent=2)+'\n')
    # Preserve concrete installation paths, including duplicate copies, without
    # changing the established deduplicated severity gate.
    locations=[]
    for report in reports:
        for v in report['advisories']:
            if v.get('fixed'):
                locations.append({'services':report['services'],**{k:v.get(k) for k in ('id','package','installed','fixed','severity','target','ecosystem','package_path','package_identifier','package_id')}})
    (out/'fix-locations.json').write_text(json.dumps({'release':release['aio_commit'],'locations':locations},indent=2)+'\n')
    (out/'report.json').write_text(json.dumps(payload,indent=2)+'\n')
    count=sum(len(x['vulnerabilities']) for x in reports)
    print('Release image scan:',count,'findings across all severities')
    return bool(count)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--scanner',default='trivy');a=p.parse_args()
    scanner=shutil.which(a.scanner)
    if not scanner:p.error('Install and verify the approved Trivy scanner independently')
    return scan(a.instance,scanner,a.output)
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as e:sys.exit('Scan incomplete: '+type(e).__name__)
