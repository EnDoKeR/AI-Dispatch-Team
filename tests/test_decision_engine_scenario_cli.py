import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_decision_engine_scenarios as scenario_cli


SCRIPT_PATH = Path("scripts/run_decision_engine_scenarios.py")


class DecisionEngineScenarioCliTest(unittest.TestCase):
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
        self.assertIn("DECISIONENGINE SCENARIO DRY-RUN", result.stdout)
        self.assertIn("Total scenarios: 12", result.stdout)
        self.assertIn("Passed: 12", result.stdout)
        self.assertIn("Failed: 0", result.stdout)

    def test_cli_prints_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(
            "DRY RUN ONLY - synthetic DecisionEngine scenarios only",
            result.stdout,
        )

    def test_cli_prints_scenario_lines(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("clean_match_good_rate", result.stdout)
        self.assertIn("weak_exit_market", result.stdout)
        self.assertIn("parser_low_confidence_field", result.stdout)

    def test_cli_does_not_import_forbidden_runtime_layers(self):
        source = inspect.getsource(scenario_cli).lower()

        forbidden_terms = [
            "telegram",
            "dispatch_case",
            "market_models",
            "marketload",
            "case_event_builder",
            "event_logger",
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
