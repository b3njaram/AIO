"""Trusted private recovery media. Checksums detect corruption, not malicious tampering."""
import hashlib,json,os,re,subprocess,tarfile
from pathlib import Path,PurePosixPath
HELPER='alpine:3.22@sha256:49340b346798875b5592e5d420241f2f9cfba5f47e62ebb1446a1b34734e898f'
REPOS={'navidrome','movies'}
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def cmd(*args):return subprocess.check_output(args,text=True).strip()
def archive(repo,sha,dest):
    if not re.fullmatch('[a-f0-9]{40}',sha) or cmd('git','-C',str(repo),'rev-parse',sha+'^{commit}')!=sha:raise ValueError('Exact source commit unavailable')
    subprocess.run(['git','-C',str(repo),'archive','--format=tar.gz','--output='+str(dest),sha],check=True)
def verify(kit,release):
    kit=Path(kit)
    manifest=kit/'kit.json'
    if kit.is_symlink() or manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size>65536:raise ValueError('Invalid recovery kit')
    m=json.loads(manifest.read_text())
    pins=release.get('source_pins',{})
    if set(pins)-REPOS or any(not isinstance(v,str) or not re.fullmatch('[a-f0-9]{40}',v) for v in pins.values()):raise ValueError('Invalid source pins')
    if m.get('schema')!=1 or m.get('release')!=release['aio_commit'] or m.get('source_pins')!=pins or not re.fullmatch('sha256:[a-f0-9]{64}',m.get('helper_id','')) or m.get('helper_reference')!=HELPER:raise ValueError('Kit does not match backup release')
    expected={'aio-source.tar.gz','helper.tar.gz',*(x+'-source.tar.gz' for x in pins)}
    if set(m['files'])!=expected or set(x.name for x in kit.iterdir())!=expected|{'kit.json'}:raise ValueError('Unexpected recovery kit files')
    for name,sha in m['files'].items():
        p=kit/name
        if p.is_symlink() or not p.is_file() or digest(p)!=sha:raise ValueError('Recovery kit checksum mismatch')
    return m
def extract_source(source,dest):
    # Only regular files and directories. No link traversal, device files,
    # duplicate paths or archive-supplied ownership. Preserve executable bits.
    with tarfile.open(source,'r:gz') as t:
        seen=set()
        for member in t:
            p=PurePosixPath(member.name)
            if p.is_absolute() or '..' in p.parts or not p.parts or '.git' in p.parts or str(p) in seen or not (member.isfile() or member.isdir()):raise ValueError('Unsupported source archive member')
            seen.add(str(p))
        t.extractall(dest,filter='data')
def load_helper(kit,m):
    subprocess.run(['docker','image','load','-i',str(kit/'helper.tar.gz')],check=True)
    identity=m['helper_id'];alias='jobbi-recovery/helper:'+identity.split(':')[1]
    subprocess.run(['docker','image','tag',identity,alias],check=True)
    if cmd('docker','image','inspect','--format','{{.Id}}',alias)!=identity:raise ValueError('Restore helper image identity mismatch')
    return alias
