import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_current_built_events_normalization_report as built_cli


SCRIPT_PATH = Path("scripts/run_current_built_events_normalization_report.py")


class CurrentBuiltEventsNormalizationReportCliTest(unittest.TestCase):
    def test_cli_exists(self):
        self.assertTrue(SCRIPT_PATH.exists())

    def test_cli_prints_total_events(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CURRENT BUILT-EVENTS NORMALIZATION REPORT DRY-RUN", result.stdout)
        self.assertIn("Total events: 9", result.stdout)

    def test_cli_prints_known_unknown_counts(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("Known events: 8", result.stdout)
        self.assertIn("Unknown events: 1", result.stdout)

    def test_cli_prints_warnings(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("Warnings: 4", result.stdout)
        self.assertIn("missing_case_id: 1", result.stdout)
        self.assertIn("missing_timestamp_utc: 1", result.stdout)
        self.assertIn("missing_source: 1", result.stdout)
        self.assertIn("unknown_event_type: 1", result.stdout)

    def test_cli_prints_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(
            "DRY RUN ONLY - current built-events normalization report, no runtime data read",
            result.stdout,
        )

    def test_cli_uses_synthetic_fixtures_only(self):
        source = inspect.getsource(built_cli).lower()

        self.assertIn("current_built_event_samples", source)
        self.assertNotIn("data/", source)
        self.assertNotIn("dispatch_cases", source)
        self.assertNotIn("dispatch_events", source)
        self.assertNotIn("open(", source)

    def test_cli_has_no_forbidden_imports(self):
        source = inspect.getsource(built_cli).lower()
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
