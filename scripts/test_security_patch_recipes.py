"""Static safety regressions for the package update recipes; runtime tests are CI."""
import os,re,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATCHES=ROOT/'deploy/security-patches'
class Tests(unittest.TestCase):
    def test_shell_syntax_and_safety(self):
        for filename in ('debian-patch.sh','alpine-patch.sh'):
            p=PATCHES/filename
            subprocess.run(['sh','-n',str(p)],check=True)
            s=p.read_text()
            for bad in ('--allow-unauthenticated','--allow-untrusted','--allow-downgrades'):
                self.assertNotIn(bad,s)
        deb=(PATCHES/'debian-patch.sh').read_text()
        self.assertIn('--only-upgrade --no-remove',deb)
        self.assertIn('test "$ID" = debian\ntest "$VERSION_CODENAME" = "$suite"',deb)
        self.assertIn('signed-by=/usr/share/keyrings/debian-archive-keyring.gpg',deb)
        self.assertIn('dpkg --compare-versions "$actual" ge "$minimum"',deb)
        alpine=(PATCHES/'alpine-patch.sh').read_text()
        self.assertIn('comm -23',alpine)
        self.assertIn('case "$(apk version -t "$actual" "$minimum")"',alpine)
    def test_alpine_build_ignores_runtime_only_tmpdir(self):
        script=(PATCHES/'alpine-patch.sh').read_text()
        # Exercise exact workspace setup and cleanup with a missing inherited TMPDIR.
        match=re.search(r'^export TMPDIR=/tmp\nwork=.*\ntrap .* EXIT$',script,re.M)
        self.assertIsNotNone(match)
        with tempfile.TemporaryDirectory() as root:
            missing=str(Path(root)/'runtime-only'/'missing')
            result=subprocess.check_output(
                ['sh','-eu','-c',match.group(0)+'\n test -d "$work"\n printf "%s\\n" "$work"'],
                text=True,env={**os.environ,'TMPDIR':missing}).strip()
            self.assertTrue(result.startswith('/tmp/jobbi-patch.'))
            self.assertFalse(Path(result).exists())
            self.assertFalse(Path(missing).exists())
    def test_every_candidate_has_pinned_base_and_package_floors(self):
        compose=(ROOT/'deploy/compose.yaml').read_text()
        services=('prowlarr','navidrome','immich-redis','pihole','immich-db','immich-server','immich-machine-learning','nextcloud')
        for service in services:
            block=re.search(r'^  '+service+r':\n((?:    [^\n]*\n)+)',compose,re.M).group(1)
            self.assertIn('context: ./security-patches',block)
            self.assertRegex(block,r"BASE_IMAGE: '[^']+@sha256:[0-9a-f]{64}'")
            self.assertRegex(block,r"PACKAGE_FLOORS: '[^']+=[^']+'")
if __name__=='__main__':unittest.main()
