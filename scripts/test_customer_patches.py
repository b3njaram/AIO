import tempfile,unittest
from pathlib import Path
from customer_patches import normalize_playlist_visibility, migrate
class PatchTests(unittest.TestCase):
    def test_incremental_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);music=root/'sources/navidrome/jobbi-music/server/index.js';music.parent.mkdir(parents=True)
            music.write_text("async function subsonic(){\n  return data;\n}\nconst route = handler")
            movies=root/'sources/movies/backend/auth.js';movies.parent.mkdir(parents=True)
            movies.write_text("httpOnly: true, sameSite: 'lax'\nhttpOnly: true, sameSite: 'lax'")
            m=music.parent.parent/'Dockerfile'
            m.write_text('FROM node:22-alpine AS build\nFROM node:22-alpine\nUSER node\nEXPOSE 3131\n')
            b=movies.parent/'Dockerfile'
            b.write_text('FROM node:20-alpine\nRUN apk add --no-cache python3 make g++ ffmpeg\nRUN npm install --omit=dev\n')
            migrate(root,{'navidrome':'pin','movies':'pin'},2)
            self.assertIn('sha256:',m.read_text())
            self.assertIn('apk del .jobbi-build-deps',b.read_text())
            self.assertNotIn('FROM node:20-alpine',b.read_text())
            self.assertIn("Object.hasOwn(p,'public')",music.read_text())
            self.assertEqual(movies.read_text().count('JOBBI_PRIVATE_HTTPS'),2)
            before=music.read_bytes();migrate(root,{'navidrome':'pin'},5);self.assertEqual(music.read_bytes(),before)
    def test_unrecognized_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);music=root/'sources/navidrome/jobbi-music/server/index.js';music.parent.mkdir(parents=True);music.write_text('unexpected')
            with self.assertRaises(ValueError):normalize_playlist_visibility(root)
            self.assertEqual(music.read_text(),'unexpected')
if __name__=='__main__':unittest.main()
