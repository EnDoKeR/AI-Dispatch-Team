import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_case_event_normalizer_report as normalizer_cli


SCRIPT_PATH = Path("scripts/run_case_event_normalizer_report.py")


class CaseEventNormalizerReportCliTest(unittest.TestCase):
    def test_cli_script_exists(self):
        self.assertTrue(SCRIPT_PATH.exists())

    def test_cli_prints_total_events(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NORMALIZED CASE EVENT WRAPPER REPORT DRY-RUN", result.stdout)
        self.assertIn("Total events: 8", result.stdout)
        self.assertIn("Normalized events: 8", result.stdout)

    def test_cli_prints_event_group_counts(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("Event group counts:", result.stdout)
        self.assertIn("load_level: 5", result.stdout)
        self.assertIn("search_reporting: 1", result.stdout)
        self.assertIn("unknown: 1", result.stdout)

    def test_cli_prints_warnings(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("Warnings: 3", result.stdout)
        self.assertIn("missing_case_id: 2", result.stdout)
        self.assertIn("unknown_event_type: 1", result.stdout)

    def test_cli_prints_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(
            "DRY RUN ONLY - normalized event wrapper report, no events written",
            result.stdout,
        )

    def test_cli_does_not_read_runtime_data(self):
        source = inspect.getsource(normalizer_cli).lower()

        self.assertIn("normalized_event_wrapper_cases", source)
        self.assertNotIn("data/", source)
        self.assertNotIn("dispatch_cases.jsonl", source)
        self.assertNotIn("dispatch_events.jsonl", source)
        self.assertNotIn("open(", source)

    def test_cli_has_no_forbidden_imports(self):
        source = inspect.getsource(normalizer_cli).lower()

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
