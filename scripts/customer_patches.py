"""AIO-only deterministic patches to pinned public upstream checkout."""
from pathlib import Path
def apply(instance,repo):
    if repo!='movies':return
    p=Path(instance)/'sources/movies/backend/db.js'
    old="INSERT INTO profiles (user_id, name, avatar, kids) VALUES (?, ?, 0, 0)"
    new="INSERT INTO profiles (user_id, name, avatar, kids, max_age) VALUES (?, ?, 0, 0, 18)"
    s=p.read_text()
    if s.count(old)!=1:raise ValueError('Unexpected pinned StreamHub default profile SQL')
    p.write_text(s.replace(old,new))
