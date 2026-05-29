import contextlib
import io
from pathlib import Path
import unittest

from scripts import run_parser_scenarios


class ParserScenarioCliTests(unittest.TestCase):
    def test_cli_script_exists(self):
        self.assertTrue(Path("scripts/run_parser_scenarios.py").exists())

    def test_cli_prints_dry_run_warning(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = run_parser_scenarios.main()

        text = output.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("DRY RUN ONLY - synthetic parser scenarios only", text)

    def test_cli_prints_total_passed_failed(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            run_parser_scenarios.main()

        text = output.getvalue()

        self.assertIn("PARSER SCENARIO DRY RUN", text)
        self.assertIn("Total scenarios:", text)
        self.assertIn("Passed:", text)
        self.assertIn("Failed:", text)
        self.assertIn("clean_ratecon_parser_output", text)
        self.assertIn("missing_broker_mc", text)

    def test_cli_uses_synthetic_fixtures_only(self):
        source = Path("scripts/run_parser_scenarios.py").read_text(encoding="utf-8")

        self.assertIn("tests.fixtures.parser_expected_outputs", source)
        self.assertNotIn("private_ratecons", source)
        self.assertNotIn("data/private", source)

    def test_cli_does_not_read_private_files_or_import_integrations(self):
        source = Path("scripts/run_parser_scenarios.py").read_text(
            encoding="utf-8"
        ).lower()

        forbidden = [
            "pypdf",
            "pdfreader",
            "pytesseract",
            "gspread",
            "google.oauth",
            "gmail",
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "event_logger",
            "scheduler",
            "threading",
            "googlemaps",
            "dat_api",
            "app.load_intake",
            "open(",
            "read_text(",
            "read_bytes(",
            "write_text(",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
