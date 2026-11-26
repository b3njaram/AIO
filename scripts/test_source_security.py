import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("audit", Path(__file__).with_name("source-security.py"))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class SourceReportTests(unittest.TestCase):
    def test_report_keeps_location_without_matched_secret(self):
        scan = {"Results": [{"Target": "example.env", "Secrets": [{
            "RuleID": "example-token", "Severity": "HIGH", "StartLine": 7,
            "Match": "synthetic-sensitive-bytes", "Code": {"Lines": ["synthetic-sensitive-bytes"]}
        }]}]}
        rows = audit.locations(scan)
        self.assertEqual(rows[0]["line"], 7)
        self.assertEqual(rows[0]["file"], "example.env")
        self.assertNotIn("synthetic-sensitive-bytes", json.dumps(rows))
