#!/usr/bin/env python3
"""Encrypted, customer-owned offsite archive export/import. Never deletes a backup."""
import argparse,hashlib,json,os,re,subprocess,sys,tarfile,tempfile
from pathlib import Path
from restore import verified_archives,metadata,checksum
from backup_mount import mount_identity
NAME=re.compile(r'[A-Za-z0-9_-]+\.tar\.gz|SHA256SUMS')
def validate(path,project=None):
    if path.is_symlink() or not path.is_dir() or (path/'SHA256SUMS').is_symlink():raise ValueError('Unsafe archive directory')
    archives=verified_archives(path)
    env,_,_=metadata(archives['instance.tar.gz'])
    if not re.fullmatch('jobbi-[a-z0-9-]+',env.get('COMPOSE_PROJECT_NAME','')) or project and env['COMPOSE_PROJECT_NAME']!=project:raise ValueError('Backup project mismatch')
    return archives
def export(path,output,recipient):
    archives=validate(path)
    if not re.fullmatch(r'age1[023456789acdefghjklmnpqrstuvwxyz]{58}',recipient):raise ValueError('Use a customer-owned native age public recipient')
    if output.exists() or output.is_symlink() or not output.parent.is_dir() or output.parent==path or path in output.parents:raise ValueError('Use a new output outside the source archive')
    os.umask(0o077)
    with tempfile.NamedTemporaryFile(dir=output.parent,delete=False) as tmp:
        p=Path(tmp.name)
        try:
            # age ciphertext is streamed directly to disk; no intermediate plaintext bundle.
            with subprocess.Popen(['age','-r',recipient],stdin=subprocess.PIPE,stdout=tmp,stderr=subprocess.DEVNULL) as proc:
                try:
                    with tarfile.open(fileobj=proc.stdin,mode='w|') as tar:
                        for name in ['SHA256SUMS',*sorted(archives)]:
                            tar.add(path/name,arcname=name,recursive=False)
                finally:proc.stdin.close()
                if proc.wait()!=0:raise ValueError('Encryption failed')
            tmp.flush();os.fsync(tmp.fileno());os.chmod(p,0o600)
            # Exclusive hard link: never overwrite an earlier encrypted backup.
            os.link(p,output)
        finally:p.unlink(missing_ok=True)
    print('Encrypted archive written; perform a decrypt/verify drill using the customer-held recovery identity.')
def recover(source,destination,identity,expected_project,expected_mount):
    if source.is_symlink() or not source.is_file() or destination.exists() or destination.is_symlink() or not destination.parent.is_dir():raise ValueError('Use a regular encrypted source and new destination')
    if mount_identity(destination.parent)!=expected_mount:raise ValueError('Destination mount identity changed')
    if identity.is_symlink() or not identity.is_file() or identity.stat().st_mode&0o077:raise ValueError('Keep recovery identity private (mode 0600)')
    os.umask(0o077)
    with tempfile.TemporaryDirectory(dir=destination.parent,prefix='.jobbi-decrypt-') as temp:
        root=Path(temp);seen=set()
        with subprocess.Popen(['age','-d','-i',str(identity),str(source)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) as proc:
            try:
                with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
                    for m in tar:
                        if not NAME.fullmatch(m.name) or m.name in seen or not m.isfile():raise ValueError('Unsafe bundle member')
                        seen.add(m.name)
                        with (root/m.name).open('xb') as out:
                            import shutil
                            shutil.copyfileobj(tar.extractfile(m),out)
                        # No archived ownership or permissions are applied.
                # Consume the entire authenticated age stream before trusting contents.
                while proc.stdout.read(1024*1024):pass
                if proc.wait()!=0:raise ValueError('Decryption/authentication failed')
            finally:
                proc.stdout.close()
                if proc.poll() is None:proc.kill();proc.wait()
        archives=validate(root,expected_project)
        if seen!={'SHA256SUMS',*archives}:raise ValueError('Unexpected archive members')
        # Atomic directory rename; destination reserved exclusively as an empty dir.
        destination.mkdir(mode=0o700)
        root.rename(destination)
    print('Decrypted archive integrity and project identity verified. Restore into a new stopped instance separately.')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['export','import']);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);p.add_argument('--recipient');p.add_argument('--identity',type=Path);p.add_argument('--project');p.add_argument('--mount-id');a=p.parse_args()
    if a.action=='export':
        if not a.recipient:p.error('Customer public age recipient required')
        export(a.source.absolute(),a.destination.absolute(),a.recipient)
    else:
        if not a.identity or not a.project or not a.mount_id:p.error('Recovery identity, exact project and approved destination mount fingerprint required')
        recover(a.source.absolute(),a.destination.absolute(),a.identity.absolute(),a.project,a.mount_id)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,tarfile.TarError,subprocess.SubprocessError) as e:sys.exit('Encrypted backup operation stopped: '+str(e))
