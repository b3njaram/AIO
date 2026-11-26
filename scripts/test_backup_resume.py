import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ResumeTests(unittest.TestCase):
    def test_failed_restart_keeps_exact_service_list_for_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            instance=root/'test'
            instance.mkdir()
            (instance/'.env').write_text('COMPOSE_PROJECT_NAME=jobbi-test\nINSTANCE_DIR='+str(instance)+'\n')
            journal=instance/'.backup-running-services'
            journal.write_text('dashboard\nuptime-kuma\n')
            docker=root/'docker'
            docker.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$TEST_ARGS"\nexit "$TEST_EXIT"\n')
            docker.chmod(0o700)
            args=root/'args'
            env={**os.environ,'PATH':str(root)+':'+os.environ['PATH'],'TEST_ARGS':str(args),'TEST_EXIT':'1'}
            cmd=['bash',str(Path(__file__).with_name('backup.sh')),str(instance),'--resume']
            self.assertNotEqual(subprocess.run(cmd,env=env,capture_output=True).returncode,0)
            self.assertTrue(journal.is_file())
            subprocess.run(cmd,env={**env,'TEST_EXIT':'0'},capture_output=True,check=True)
            self.assertFalse(journal.exists())
            self.assertEqual(args.read_text().splitlines()[-3:],['start','dashboard','uptime-kuma'])
