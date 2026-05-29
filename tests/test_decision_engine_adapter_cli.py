import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_decision_engine_adapter_dry_run as adapter_cli


SCRIPT_PATH = Path("scripts/run_decision_engine_adapter_dry_run.py")


class DecisionEngineAdapterCliTest(unittest.TestCase):
    def test_cli_script_exists(self):
        self.assertTrue(SCRIPT_PATH.exists())

    def test_cli_prints_decision_result_from_subprocess(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DECISIONENGINE ADAPTER DRY-RUN", result.stdout)
        self.assertIn("DecisionResult decision: REVIEW_ONCE", result.stdout)
        self.assertIn("DecisionResult JSON:", result.stdout)
        self.assertIn('"decision": "REVIEW_ONCE"', result.stdout)
        self.assertIn("RATE_CHECK_REQUIRED", result.stdout)

    def test_cli_prints_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(
            "DRY RUN ONLY - adapter preview only, no runtime behavior changed",
            result.stdout,
        )

    def test_cli_does_not_import_forbidden_runtime_layers(self):
        source = inspect.getsource(adapter_cli).lower()

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
