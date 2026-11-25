#!/usr/bin/env python3
"""Consistent online SQLite backup of the owner business ledger, never overwrites."""
import argparse,datetime as dt,hashlib,json,os,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEFAULT=Path.home()/'.local/share/jobbi-business/cash.sqlite3'
def backup(source,destination):
    source=Path(source).expanduser().resolve();destination=Path(destination).expanduser().resolve()
    if not source.is_file() or source.stat().st_mode&0o077:raise ValueError('Source ledger missing or not private')
    if not destination.is_dir() or destination==ROOT or ROOT in destination.parents:raise ValueError('Use an existing private destination outside Git')
    if source.stat().st_dev==destination.stat().st_dev:raise ValueError('Use a separate mounted filesystem for business backups')
    os.umask(0o077)
    folder=destination/('jobbi-business-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(mode=0o700)
    path=folder/'cash.sqlite3'
    try:
        with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=20) as src,sqlite3.connect(path) as dst:
            src.backup(dst,pages=100,sleep=.05)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup failed integrity check')
            if dst.execute('PRAGMA foreign_key_check').fetchone() is not None:raise ValueError('Backup failed foreign key check')
        path.chmod(0o600)
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
        sha=digest.hexdigest()
        (folder/'SHA256SUMS').write_text(sha+'  cash.sqlite3\n')
        return folder
    except Exception:
        # Leave incomplete folder for inspection, without a completion checksum.
        raise
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination',type=Path);p.add_argument('--source',type=Path,default=DEFAULT);a=p.parse_args()
    print('Verified private business backup:',backup(a.source,a.destination))
    print('Contains financial/customer records. Encrypt at rest; keep credentials separate.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,sqlite3.Error) as e:sys.exit('Business backup failed: '+str(e))
