#!/usr/bin/env python3
"""Export independent customer music app sources from the pinned upstream checkout."""
import argparse,json,os,re,subprocess,sys,urllib.parse
from pathlib import Path
PIN='83684735def8138100dc1e304d62f0f1ca556357'
PERSONAL='https://music.jobbisoft.com.mx'
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path,help='Instance sources/navidrome checkout')
    p.add_argument('--output',required=True,type=Path,help='New empty destination outside existing deployment')
    p.add_argument('--origin',required=True,help='Customer-approved HTTPS music origin, no path')
    a=p.parse_args()
    origin=a.origin.rstrip('/')
    u=urllib.parse.urlsplit(origin)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.path or u.query or u.fragment or not re.fullmatch(r'[A-Za-z0-9.-]+',u.hostname) or u.hostname=='music.jobbisoft.com.mx' or not re.fullmatch(r'https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?',origin):
        p.error('Enter a customer HTTPS origin, never the personal server')
    source=a.source.expanduser().resolve();dest=a.output.expanduser().resolve()
    if dest.exists() or source in dest.parents or dest in source.parents:p.error('Use a new separate output directory')
    head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if head!=PIN:p.error('Unexpected upstream revision; review before preparing mobile source')
    os.umask(0o077);dest.mkdir(parents=True)
    # Export the committed source, not local modified files, .env or credentials.
    proc=subprocess.Popen(['git','-C',str(source),'archive',PIN,'jobbi-music/android-native','jobbi-music/ios-native'],stdout=subprocess.PIPE)
    try:subprocess.run(['tar','-xf','-','-C',str(dest)],stdin=proc.stdout,check=True)
    finally:proc.stdout.close()
    if proc.wait()!=0:raise ValueError('Source export failed')
    root=dest/'jobbi-music'
    targets=[root/'ios-native/JobbiMusic',root/'android-native/app/src/main']
    changed=[]
    for folder in targets:
        for file in folder.rglob('*'):
            if file.is_file() and file.suffix in ('.swift','.kt','.java','.xml','.plist'):
                data=file.read_text()
                if PERSONAL in data:
                    file.write_text(data.replace(PERSONAL,origin));changed.append(str(file.relative_to(dest)))
    if len(changed)<3:raise ValueError('Expected server defaults were not all found')
    gradle=root/'android-native/app/build.gradle.kts'
    data=gradle.read_text()
    old='applicationId = "com.jobbisoft.music.nativeplayer"'
    if old not in data:raise ValueError('Unexpected Android application ID')
    gradle.write_text(data.replace(old,'applicationId = "com.jobbisoft.music.commercial"'))
    project=root/'ios-native/project.yml'
    data=project.read_text()
    if 'PRODUCT_BUNDLE_IDENTIFIER: com.jobbisoft.jobbi.music' not in data:raise ValueError('Unexpected iOS bundle ID')
    project.write_text(data.replace('PRODUCT_BUNDLE_IDENTIFIER: com.jobbisoft.jobbi.music','PRODUCT_BUNDLE_IDENTIFIER: com.jobbisoft.jobbi.music.commercial'))
    report={'upstream':PIN,'default_origin':origin,'changed_files':changed,'android_id':'com.jobbisoft.music.commercial','ios_id':'com.jobbisoft.jobbi.music.commercial','status':'source prepared only; build, signing and device tests pending'}
    (dest/'commercial-build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    print('No signed binary produced. See docs/MOBILE.md.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.CalledProcessError) as e:sys.exit('Stopped: '+str(e))
