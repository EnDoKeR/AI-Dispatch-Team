import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_decision_result_timeline_preview as preview_cli


SCRIPT_PATH = Path("scripts/run_decision_result_timeline_preview.py")


class DecisionResultTimelinePreviewCliTest(unittest.TestCase):
    def test_cli_script_exists(self):
        self.assertTrue(SCRIPT_PATH.exists())

    def test_cli_prints_total_and_summary(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DECISIONRESULT TIMELINE PREVIEW DRY-RUN", result.stdout)
        self.assertIn("Total previews: 8", result.stdout)
        self.assertIn("Decision summary:", result.stdout)
        self.assertIn("Risk flag summary:", result.stdout)
        self.assertIn("MATCH: 1", result.stdout)
        self.assertIn("REVIEW_ONCE: 5", result.stdout)
        self.assertIn("BLOCK: 2", result.stdout)

    def test_cli_prints_preview_rows(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn("CASE-PREVIEW-1", result.stdout)
        self.assertIn("AI_DECISION_CREATED", result.stdout)
        self.assertIn("RATE_CHECK_REQUIRED", result.stdout)

    def test_cli_prints_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(
            "DRY RUN ONLY - DecisionResult timeline preview, no events written",
            result.stdout,
        )

    def test_cli_does_not_read_runtime_data(self):
        source = inspect.getsource(preview_cli).lower()

        self.assertIn("decision_result_timeline_previews", source)
        self.assertNotIn("dispatch_cases.jsonl", source)
        self.assertNotIn("dispatch_events.jsonl", source)
        self.assertNotIn("data/", source)
        self.assertNotIn("open(", source)

    def test_cli_has_no_forbidden_imports(self):
        source = inspect.getsource(preview_cli).lower()

        forbidden_terms = [
            "telegram",
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
            "apply_search_request",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
