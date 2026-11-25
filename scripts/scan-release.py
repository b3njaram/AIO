#!/usr/bin/env python3
"""Scan exact local container image IDs with a separately verified Trivy installation."""
import argparse,datetime as dt,importlib.util,json,os,re,shutil,subprocess,sys,tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('inventory',Path(__file__).with_name('release-inventory.py'))
inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
def summarize(data):
    if not isinstance(data,dict) or not isinstance(data.get('Results'),list) or not data['Results']:raise ValueError('No scanner result sections; cannot certify coverage')
    findings=set();licenses=set()
    for section in data['Results']:
        for v in section.get('Vulnerabilities') or []:
            severity=v.get('Severity','UNKNOWN').upper()
            if severity in ('HIGH','CRITICAL','UNKNOWN'):
                findings.add((v.get('VulnerabilityID','unknown'),v.get('PkgName','unknown'),v.get('InstalledVersion',''),v.get('FixedVersion',''),severity))
        for license in section.get('Licenses') or []:
            name=license.get('Name')
            if isinstance(name,str) and len(name)<200:licenses.add(name)
    return {'vulnerabilities':[dict(zip(('id','package','installed','fixed','severity'),x)) for x in sorted(findings)],'license_names':sorted(licenses),'sections':len(data['Results'])}
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
            cmd=[scanner,'image','--image-src','docker','--scanners','vuln,license','--format','json','--output',str(raw),'--timeout','15m',image]
            # Do not ignore unfixed findings or use an unreviewed ignore file in the repo.
            subprocess.run(cmd,cwd=tmp,check=True,timeout=950)
            result=summarize(json.loads(raw.read_text()))
        reports.append({'image':image,'services':sorted(services),**result})
        print('Scanned',','.join(sorted(services)),':',len(result['vulnerabilities']),'high/critical/unknown findings',flush=True)
    payload={'schema':1,'at':dt.datetime.now(dt.timezone.utc).isoformat(),'release':release['aio_commit'],'scanner':version.strip(),'images':reports,'policy':'All high, critical and unknown-severity findings require release review; license discovery is not a compliance determination.'}
    (out/'report.json').write_text(json.dumps(payload,indent=2)+'\n')
    count=sum(len(x['vulnerabilities']) for x in reports)
    print('Release image scan:',count,'high/critical/unknown findings; review required' if count else 'findings at gated severities')
    return bool(count)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--scanner',default='trivy');a=p.parse_args()
    scanner=shutil.which(a.scanner)
    if not scanner:p.error('Install and verify the approved Trivy scanner independently')
    return scan(a.instance,scanner,a.output)
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as e:sys.exit('Scan incomplete: '+type(e).__name__)
