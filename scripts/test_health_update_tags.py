import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('health_snapshot', Path(__file__).with_name('health-snapshot.py'))
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class ReleaseTagTests(unittest.TestCase):
    def test_lightweight_and_annotated_tags(self):
        commit = '1' * 40
        tag = 'refs/tags/jobbi-home-v1.10.0'
        direct = f'{commit}\t{tag}'
        annotated = [f'{"a" * 40}\t{tag}', f'{direct}^{{}}']
        older = f'{"2" * 40}\trefs/tags/jobbi-home-v1.9.0'
        for lines in ([direct], annotated, list(reversed(annotated))):
            with self.subTest(lines=lines), patch.object(health.subprocess, 'run') as run:
                run.return_value.stdout = '\n'.join([*lines, older])
                status = health.update_status({'aio_commit': commit}, check=True)
                self.assertNotIn('--refs', run.call_args.args[0])
                self.assertEqual(status, {'state': 'current', 'release': 'jobbi-home-v1.10.0'})
