import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_decision_engine_comparison_report as comparison_cli


SCRIPT_PATH = Path("scripts/run_decision_engine_comparison_report.py")


class DecisionEngineComparisonReportCliTest(unittest.TestCase):
    def test_cli_script_exists(self):
        self.assertTrue(SCRIPT_PATH.exists())

    def test_cli_prints_summary_from_subprocess(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DECISIONENGINE COMPARISON REPORT DRY-RUN", result.stdout)
        self.assertIn("Total comparisons: 8", result.stdout)
        self.assertIn("Decision matches: 8", result.stdout)
        self.assertIn("Decision mismatches: 0", result.stdout)
        self.assertIn("Category matches: 8", result.stdout)
        self.assertIn("Category mismatches: 0", result.stdout)

    def test_cli_prints_fixture_rows(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("SYN-COMP-LOAD-1", result.stdout)
        self.assertIn("SYN-COMP-REF-1", result.stdout)
        self.assertIn("REVIEW_ONCE -> REVIEW_ONCE", result.stdout)
        self.assertIn("RATE_CHECK_REQUIRED", result.stdout)

    def test_cli_prints_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(
            "DRY RUN ONLY - comparison report only, no runtime behavior changed",
            result.stdout,
        )

    def test_cli_uses_synthetic_fixtures_only(self):
        source = inspect.getsource(comparison_cli).lower()

        self.assertIn("decision_engine_comparison_loads", source)
        self.assertNotIn("data/private", source)
        self.assertNotIn("current_loads", source)

    def test_cli_does_not_import_forbidden_layers(self):
        source = inspect.getsource(comparison_cli).lower()

        forbidden_terms = [
            "telegram",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "market_models",
            "pypdf",
            "gspread",
            "googlemaps",
            "dat_api",
            "apscheduler",
            "threading",
            "sqlite",
            "jsonl",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
