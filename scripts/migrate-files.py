#!/usr/bin/env python3
"""Verified non-destructive migration of customer-owned media/files to a private staging area."""
import argparse,hashlib,json,os,re,shutil,stat,sys
from pathlib import Path
KINDS={'music':{'.flac','.mp3','.m4a','.aac','.ogg','.opus','.wav','.alac','.aiff','.wma'},'movies':{'.mp4','.mkv','.mov','.avi','.webm','.m4v','.srt','.vtt'},'photos':{'.jpg','.jpeg','.png','.heic','.heif','.webp','.tif','.tiff','.dng','.raw','.mov','.mp4','.xmp'},'files':None}
def plan(source,kind):
    rows=[];skipped=0
    for base,dirs,files in os.walk(source,followlinks=False):
        root=Path(base)
        for d in dirs:
            if (root/d).is_symlink():raise ValueError('Source contains a symbolic link directory')
        for n in sorted(files):
            p=root/n;s=p.lstat()
            if not stat.S_ISREG(s.st_mode):raise ValueError('Source contains link or special file')
            if KINDS[kind] is not None and p.suffix.lower() not in KINDS[kind]:skipped+=1;continue
            rel=p.relative_to(source).as_posix()
            if len(rel)>4096 or any(ord(c)<32 for c in rel):raise ValueError('Unsupported filename')
            rows.append({'path':rel,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'dev':s.st_dev})
            if len(rows)>100000:raise ValueError('Split into batches of at most 100000 files')
    if not rows:raise ValueError('No supported files')
    return sorted(rows,key=lambda x:x['path']),skipped
def copy(source,dest,rows):
    result=[]
    for row in rows:
        rel=row['path'];p=source/rel;out=dest/rel
        if p.resolve(strict=True)!=p or source not in p.parents:raise ValueError('Source path changed')
        out.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as src:
            def unchanged():
                s=os.fstat(src.fileno())
                return stat.S_ISREG(s.st_mode) and (s.st_size,s.st_mtime_ns,s.st_ino,s.st_dev)==tuple(row[k] for k in ('size','mtime_ns','inode','dev'))
            if not unchanged():raise ValueError('Source changed since preview')
            h=hashlib.sha256()
            with out.open('xb') as dst:
                while b:=src.read(1024*1024):h.update(b);dst.write(b)
                dst.flush();os.fsync(dst.fileno())
            if not unchanged():raise ValueError('Source changed during copy')
        with out.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=h.hexdigest():raise ValueError('Copied bytes failed verification')
        result.append({'path':rel,'size':row['size'],'sha256':actual})
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);p.add_argument('--kind',choices=KINDS,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    src=a.source.resolve(strict=True);dst=a.destination.expanduser().absolute();parent=dst.parent.resolve(strict=True)
    if os.geteuid()==0 or not src.is_dir() or not parent.is_dir() or dst.exists() or dst.is_symlink() or src==parent or src in parent.parents or parent in src.parents:raise ValueError('Use non-root operator, separate source and new private staging directory')
    root=Path(__file__).resolve().parents[1]
    if root==parent or root in parent.parents:raise ValueError('Keep private data outside Git')
    # Stage outside every live instance; do not write into a database or app data tree.
    for q in (parent,*parent.parents):
        if (q/'.env').is_file() and (q/'release.json').is_file():raise ValueError('Destination inside a live instance')
    rows,skipped=plan(src,a.kind);size=sum(x['size'] for x in rows)
    if shutil.disk_usage(parent).free<size+1024**3:raise ValueError('Insufficient staging space including 1 GiB reserve')
    print(json.dumps({'kind':a.kind,'files':len(rows),'bytes':size,'skipped_extensions':skipped,'preview':not a.apply},indent=2))
    if not a.apply:return
    os.umask(0o077);dst.mkdir();payload=dst/'payload';payload.mkdir()
    result=copy(src,payload,rows)
    with (dst/'manifest.json').open('x') as f:json.dump({'schema':1,'kind':a.kind,'files':result},f,indent=2)
    print('Completed verified staging. Source unchanged. Use the application native import or reviewed library copy; no live database edits.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError) as e:sys.exit('Migration stopped; preserve source and inspect partial staging: '+type(e).__name__)
