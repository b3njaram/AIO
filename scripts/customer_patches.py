"""Versioned AIO-only patches to pinned upstream customer checkouts."""
from pathlib import Path
VERSION=4
def secure_movie_cookies(instance):
    path=Path(instance)/'sources/movies/backend/auth.js'
    old="httpOnly: true, sameSite: 'lax'"
    source=path.read_text()
    if source.count(old)!=2:raise ValueError('Unexpected pinned StreamHub cookie options')
    path.write_text(source.replace(old,"secure: process.env.JOBBI_PRIVATE_HTTPS === 'true', "+old))

def apply(instance,repo,version=VERSION):
    if version not in (1,2,3,4):raise ValueError('Unsupported customer patch version')
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

    if version>=4 and repo=='navidrome':
        # Navidrome v0.64.2 Playlist.Public uses json:"public,omitempty".
        # Only normalize authenticated full playlist objects, not missing or minimal objects.
        p=Path(instance)/'sources/navidrome/jobbi-music/server/index.js'
        source=p.read_text()
        anchor="  return data;\n}\nconst route = handler"
        new="""  // Navidrome omits a false public flag in its full JSON playlist response.
  // Owner is present on full playlist objects and absent on minimal clients.
  const fullPlaylist = p => {
    if(p && typeof p.id==='string' && typeof p.owner==='string' && p.owner.trim()
       && !Object.hasOwn(p,'public')) p.public=false;
  };
  if(name==='getPlaylist') fullPlaylist(data.playlist);
  if(name==='getPlaylists') for(const p of data.playlists?.playlist||[]) fullPlaylist(p);
  return data;
}
const route = handler"""
        if source.count(anchor)!=1:raise ValueError('Unexpected pinned Subsonic response adapter')
        p.write_text(source.replace(anchor,new))
