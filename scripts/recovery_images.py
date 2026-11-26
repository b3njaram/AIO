"""Freeze registry digests and archive images that have no registry digest."""
import json
import re
import subprocess
from pathlib import Path

IMAGE_ID = re.compile(r'sha256:[0-9a-f]{64}')
DIGEST = re.compile(r'[a-z0-9][a-z0-9./:_-]*@sha256:[0-9a-f]{64}')


def image_plan(inventory):
    if inventory.get('schema') != 1 or not inventory.get('services'):
        raise ValueError('Missing image inventory')
    plan = {}
    for name, row in inventory['services'].items():
        identity = row['id']
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', name) or not IMAGE_ID.fullmatch(identity):
            raise ValueError('Invalid service image identity')
        digests = row['repo_digests']
        if not isinstance(digests, list) or any(not DIGEST.fullmatch(d) for d in digests):
            raise ValueError('Invalid registry digest')
        # Compose-built and recovered aliases can have local RepoDigests which
        # are not published to any registry.
        local = row['reference'].startswith((inventory['project']+'-', 'jobbi-recovery/image:'))
        plan[name] = (identity, sorted(digests)[0] if digests and not local else None)
    return plan


def stage(inventory, archive, deployment, all_images=False):
    plan = image_plan(inventory)
    if all_images or any(digest is None for _, digest in plan.values()):
        if archive is None:
            raise ValueError('Missing archive of locally built images')
        subprocess.run(['docker', 'image', 'load', '-i', str(archive)], check=True)
    services = {}
    for name, (identity, digest) in plan.items():
        if digest and not all_images:
            probe = ['docker', 'image', 'inspect', '--format', '{{.Id}}', digest]
            existing = subprocess.run(probe, capture_output=True, text=True)
            if existing.returncode:
                subprocess.run(['docker', 'pull', digest], check=True)
            reference = digest
        else:
            reference = 'jobbi-recovery/image:' + identity.split(':')[1]
            subprocess.run(['docker', 'image', 'tag', identity, reference], check=True)
        actual = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', reference], text=True).strip()
        if actual != identity:
            raise ValueError('Image identity mismatch for ' + name)
        services[name] = {'image': reference, 'pull_policy': 'never'}
    (deployment / 'recovery-images.json').write_text(json.dumps({'services': services}, indent=2)+'\n')

if __name__ == '__main__':
    import sys
    plan = image_plan(json.loads(Path(sys.argv[1]).read_text()))
    for image in sorted({image for image, digest in plan.values() if digest is None or "--all-images" in sys.argv[2:]}):
        print(image)
