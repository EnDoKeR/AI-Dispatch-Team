import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_decision_engine_timeline_report as timeline_cli


SCRIPT_PATH = Path("scripts/run_decision_engine_timeline_report.py")


class DecisionEngineTimelineReportCliTest(unittest.TestCase):
    def test_cli_exists(self):
        self.assertTrue(SCRIPT_PATH.exists())

    def test_cli_prints_total_and_summary(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DECISIONENGINE TIMELINE COMBINED REPORT DRY-RUN", result.stdout)
        self.assertIn("Total loads: 8", result.stdout)
        self.assertIn("MATCH: 2", result.stdout)
        self.assertIn("REVIEW_ONCE: 4", result.stdout)
        self.assertIn("BLOCK: 2", result.stdout)
        self.assertIn("Preview events: 8", result.stdout)

    def test_cli_prints_risk_flag_summary(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("RATE_MISSING: 1", result.stdout)
        self.assertIn("NO_CONESTOGA: 1", result.stdout)
        self.assertIn("BROKER_MC_MISSING: 1", result.stdout)

    def test_cli_prints_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(
            "DRY RUN ONLY - DecisionEngine timeline combined report, no events written",
            result.stdout,
        )

    def test_cli_uses_synthetic_fixtures_only(self):
        source = inspect.getsource(timeline_cli).lower()

        self.assertIn("decision_engine_combined_report_loads", source)
        self.assertNotIn("data/", source)
        self.assertNotIn("dispatch_cases.jsonl", source)
        self.assertNotIn("dispatch_events.jsonl", source)
        self.assertNotIn("open(", source)

    def test_cli_has_no_forbidden_imports(self):
        source = inspect.getsource(timeline_cli).lower()

        forbidden_terms = [
            "telegram",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "repository",
            "pypdf",
            "gspread",
            "googlemaps",
            "dat_api",
            "apscheduler",
            "threading",
            "apply_search_request",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
