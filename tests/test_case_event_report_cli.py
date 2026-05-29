import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_case_event_report as report_cli
from tests.fixtures.case_event_records import SYNTHETIC_CASE_EVENT_RECORDS


SCRIPT_PATH = Path("scripts/run_case_event_report.py")


class CaseEventReportCliTest(unittest.TestCase):
    def test_fixtures_import(self):
        self.assertGreaterEqual(len(SYNTHETIC_CASE_EVENT_RECORDS), 7)

    def test_cli_script_exists(self):
        self.assertTrue(SCRIPT_PATH.exists())

    def test_cli_prints_total_and_counts(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CASE EVENT TIMELINE REPORT DRY-RUN", result.stdout)
        self.assertIn("Total events: 7", result.stdout)
        self.assertIn("AI_DECISION_CREATED: 1", result.stdout)
        self.assertIn("load_level: 4", result.stdout)
        self.assertIn("reload_watch: 1", result.stdout)

    def test_cli_prints_unknown_event_types(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("UNCLASSIFIED_SYNTHETIC_EVENT", result.stdout)

    def test_cli_prints_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("DRY RUN ONLY - synthetic event report only", result.stdout)

    def test_cli_does_not_read_runtime_data(self):
        source = inspect.getsource(report_cli).lower()

        self.assertIn("synthetic_case_event_records", source)
        self.assertNotIn("data/", source)
        self.assertNotIn("dispatch_cases.jsonl", source)
        self.assertNotIn("open(", source)

    def test_cli_has_no_forbidden_imports(self):
        source = inspect.getsource(report_cli).lower()

        forbidden_terms = [
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "repository",
            "sqlite",
            "jsonl",
            "pypdf",
            "gspread",
            "googlemaps",
            "dat_api",
            "apscheduler",
            "threading",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
