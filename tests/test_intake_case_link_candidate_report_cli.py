import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_intake_case_link_candidate_report as candidate_cli


SCRIPT_PATH = Path("scripts/run_intake_case_link_candidate_report.py")


class TestIntakeCaseLinkCandidateReportCli(unittest.TestCase):
    def test_cli_exists(self):
        self.assertTrue(SCRIPT_PATH.exists())

    def test_cli_prints_total_and_action_counts(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("INTAKE-TO-CASE LINK CANDIDATE REPORT DRY-RUN", result.stdout)
        self.assertIn("Total candidates: 10", result.stdout)
        self.assertIn("LINK_EXISTING: 2", result.stdout)
        self.assertIn("CREATE_CASE_REVIEW: 1", result.stdout)

    def test_cli_prints_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(
            "DRY RUN ONLY - intake-to-case candidate report, no cases linked or created",
            result.stdout,
        )

    def test_cli_uses_synthetic_fixtures_only(self):
        source = inspect.getsource(candidate_cli).lower()

        self.assertIn("intake_case_link_candidates", source)
        self.assertNotIn("data/", source)
        self.assertNotIn("jsonl", source)
        self.assertNotIn("open(", source)

    def test_cli_has_no_forbidden_imports(self):
        source = inspect.getsource(candidate_cli).lower()
        forbidden_terms = [
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "repository",
            "sqlite",
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
