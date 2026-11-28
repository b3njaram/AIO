"""Versioned AIO-only patches to pinned upstream customer checkouts."""
from pathlib import Path
VERSION=5
def secure_movie_cookies(instance):
    path=Path(instance)/'sources/movies/backend/auth.js'
    old="httpOnly: true, sameSite: 'lax'"
    source=path.read_text()
    if source.count(old)!=2:raise ValueError('Unexpected pinned StreamHub cookie options')
    path.write_text(source.replace(old,"secure: process.env.JOBBI_PRIVATE_HTTPS === 'true', "+old))

def apply(instance,repo,version=VERSION):
    if version not in (1,2,3,4,5):raise ValueError('Unsupported customer patch version')
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

    if version>=4 and repo=='navidrome':normalize_playlist_visibility(instance)
    if version>=5:runtime_build(instance,repo)


def normalize_playlist_visibility(instance):
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


def migrate(instance,pins,previous):
    """Advance an already patched checkout without reapplying prior migrations."""
    if previous not in (2,3,4,5):raise ValueError('Unsupported source migration')
    if previous<3 and 'movies' in pins:secure_movie_cookies(instance)
    if previous<4 and 'navidrome' in pins:normalize_playlist_visibility(instance)
    if previous<5:
        for repo in pins:runtime_build(instance,repo)


NODE_BASE='node:22-alpine@sha256:1314fb30ec37592d5845e5a160d522c0e680972aa534549940b8d73bde88481a'
REMOVE_BUILD_TOOLS='RUN rm -rf /usr/local/lib/node_modules /opt/yarn* /root/.npm && rm -f /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack /usr/local/bin/yarn /usr/local/bin/yarnpkg && node --version'
def runtime_build(instance,repo):
    """Modify only the exact pinned customer Dockerfile; keep old patch versions reproducible."""
    if repo=='navidrome':
        p=Path(instance)/'sources/navidrome/jobbi-music/Dockerfile'
        source=p.read_text()
        anchor='USER node\nEXPOSE 3131'
        if source.count('FROM node:22-alpine')!=2 or source.count(anchor)!=1:raise ValueError('Unexpected music build source')
        source=source.replace('FROM node:22-alpine','FROM '+NODE_BASE).replace(anchor,REMOVE_BUILD_TOOLS+'\n'+anchor)
    elif repo=='movies':
        p=Path(instance)/'sources/movies/backend/Dockerfile'
        source=p.read_text()
        anchor='RUN apk add --no-cache python3 make g++ ffmpeg'
        install='RUN npm install --omit=dev'
        if source.count('FROM node:20-alpine')!=1 or source.count(anchor)!=1 or source.count(install)!=1:raise ValueError('Unexpected StreamHub build source')
        source=source.replace('FROM node:20-alpine','FROM '+NODE_BASE).replace(anchor,'RUN apk add --no-cache ffmpeg && apk add --no-cache --virtual .jobbi-build-deps python3 make g++').replace(install,install+' && apk del .jobbi-build-deps\n'+REMOVE_BUILD_TOOLS+'\nRUN node -e "const DB=require(\\x27better-sqlite3\\x27);new DB(\\x27:memory:\\x27).close()"'.replace('\\x27',"'"))
    else:raise ValueError('Unknown source repository')
    p.write_text(source)
