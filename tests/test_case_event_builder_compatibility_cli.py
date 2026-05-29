import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_case_event_builder_compatibility as compatibility_cli
from tests.fixtures.case_event_builder_outputs import (
    SYNTHETIC_CASE_EVENT_BUILDER_OUTPUTS,
)


SCRIPT_PATH = Path("scripts/run_case_event_builder_compatibility.py")


class CaseEventBuilderCompatibilityCliTest(unittest.TestCase):
    def test_fixtures_import(self):
        self.assertGreaterEqual(len(SYNTHETIC_CASE_EVENT_BUILDER_OUTPUTS), 7)

    def test_cli_script_exists(self):
        self.assertTrue(SCRIPT_PATH.exists())

    def test_cli_prints_report(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CASE EVENT BUILDER COMPATIBILITY DRY-RUN", result.stdout)
        self.assertIn("Total event samples: 7", result.stdout)
        self.assertIn("AI_DECISION_CREATED", result.stdout)
        self.assertIn("Missing base payload keys:", result.stdout)
        self.assertIn("event_group", result.stdout)

    def test_cli_prints_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(
            "DRY RUN ONLY - event builder compatibility report only",
            result.stdout,
        )

    def test_cli_does_not_read_runtime_data(self):
        source = inspect.getsource(compatibility_cli).lower()

        self.assertIn("synthetic_case_event_builder_outputs", source)
        self.assertNotIn("data/", source)
        self.assertNotIn("dispatch_cases.jsonl", source)
        self.assertNotIn("dispatch_events.jsonl", source)
        self.assertNotIn("open(", source)

    def test_cli_has_no_forbidden_imports(self):
        source = inspect.getsource(compatibility_cli).lower()

        forbidden_terms = [
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder import",
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
