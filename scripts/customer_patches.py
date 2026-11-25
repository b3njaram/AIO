"""Versioned AIO-only patches to pinned upstream customer checkouts."""
from pathlib import Path
VERSION=3
def secure_movie_cookies(instance):
    path=Path(instance)/'sources/movies/backend/auth.js'
    old="httpOnly: true, sameSite: 'lax'"
    source=path.read_text()
    if source.count(old)!=2:raise ValueError('Unexpected pinned StreamHub cookie options')
    path.write_text(source.replace(old,"secure: process.env.JOBBI_PRIVATE_HTTPS === 'true', "+old))

def apply(instance,repo,version=VERSION):
    if version not in (1,2,3):raise ValueError('Unsupported customer patch version')
    if repo=='movies':
        p=Path(instance)/'sources/movies/backend/db.js'
        old="INSERT INTO profiles (user_id, name, avatar, kids) VALUES (?, ?, 0, 0)"
        new="INSERT INTO profiles (user_id, name, avatar, kids, max_age) VALUES (?, ?, 0, 0, 18)"
        s=p.read_text()
        if s.count(old)!=1:raise ValueError('Unexpected pinned StreamHub default profile SQL')
        p.write_text(s.replace(old,new))
    if version>=2 and repo=='navidrome':
        p=Path(instance)/'sources/navidrome/jobbi-music/server/android-update.js'
        if 'export async function androidLatest(){' not in p.read_text():raise ValueError('Unexpected upstream Android release module')
        # No personal release feed or network request in the commercial edition.
        p.write_text("export function findAndroidRelease(){return {available:false};}\nexport async function androidLatest(){return {available:false,reason:'Use a compatible client or contact your server administrator for optional native builds.'};}\n")
    if version>=3 and repo=='movies':secure_movie_cookies(instance)
