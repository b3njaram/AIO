import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location('connect_movies', Path(__file__).with_name('connect-movies.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.i = Path(self.tmp.name).resolve()
        self.key = 'a' * 32
        self.config = self.i / 'data/prowlarr/config.xml'
        self.config.parent.mkdir(parents=True)
        self.config.write_text('<Config><ApiKey>'+self.key+'</ApiKey></Config>')
        self.env = self.i / '.env'
        self.base = ('INSTANCE_DIR='+str(self.i)+'\nOWNER_UID=1000\n'
                     'COMPOSE_PROJECT_NAME=jobbi-test\nBIND_IP=127.0.0.1\n'
                     'COMPOSE_PROFILES=movies\n')
        self.env.write_text(self.base+'PROWLARR_API_KEY=\n')
        for name in ('getuid', 'geteuid'):
            p = patch.object(m.os, name, return_value=1000)
            p.start()
            self.addCleanup(p.stop)
    def test_fresh_and_idempotent(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0))
        m.link(self.i, run=run)
        self.assertIn('PROWLARR_API_KEY='+self.key, self.env.read_text())
        self.assertEqual(self.env.stat().st_mode & 0o777, 0o600)
        self.assertEqual(run.call_count, 2)
        self.assertIn('--no-build', run.call_args_list[0].args[0])
        self.assertNotIn(self.key, str(run.call_args_list))
        run.reset_mock()
        m.link(self.i, run=run)
        self.assertEqual(run.call_count, 1)
    def test_existing_different_key_preserved(self):
        self.env.write_text(self.base+'PROWLARR_API_KEY='+'b'*32+'\n')
        original = self.env.read_bytes()
        run = Mock()
        with self.assertRaises(ValueError):
            m.link(self.i, run=run)
        self.assertEqual(self.env.read_bytes(), original)
        run.assert_not_called()
    def test_missing_key_does_not_mutate(self):
        self.config.unlink()
        original = self.env.read_bytes()
        run = Mock()
        with self.assertRaises(ValueError):
            m.link(self.i, run=run, sleep=lambda _: None)
        self.assertEqual(self.env.read_bytes(), original)
        run.assert_not_called()
    def test_retry_retains_generated_key(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 1))
        with self.assertRaises(ValueError):
            m.link(self.i, run=run, sleep=lambda _: None)
        self.assertIn('PROWLARR_API_KEY='+self.key, self.env.read_text())
        run = Mock(return_value=subprocess.CompletedProcess([], 0))
        m.link(self.i, run=run)
        self.assertEqual(run.call_count, 1)
