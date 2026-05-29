import contextlib
import io
from pathlib import Path
import unittest

from scripts import run_pasted_text_scenarios


class PastedTextScenarioCliTests(unittest.TestCase):
    def test_cli_script_exists(self):
        self.assertTrue(Path("scripts/run_pasted_text_scenarios.py").exists())

    def test_cli_prints_totals_and_scenarios(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = run_pasted_text_scenarios.main()

        text = output.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("PASTED TEXT SCENARIO DRY RUN", text)
        self.assertIn("Total scenarios:", text)
        self.assertIn("Passed:", text)
        self.assertIn("Failed:", text)
        self.assertIn("clean_simple_ratecon_text", text)
        self.assertIn("multiple_rates_accessorials", text)

    def test_cli_prints_dry_run_warning(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            run_pasted_text_scenarios.main()

        self.assertIn(
            "DRY RUN ONLY - synthetic pasted-text scenarios only",
            output.getvalue(),
        )

    def test_cli_uses_synthetic_fixtures_only(self):
        source = Path("scripts/run_pasted_text_scenarios.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("tests.fixtures.pasted_text_ratecon_examples", source)
        self.assertNotIn("private_ratecons", source)
        self.assertNotIn("data/private", source)

    def test_cli_has_no_private_file_reading_or_forbidden_imports(self):
        source = Path("scripts/run_pasted_text_scenarios.py").read_text(
            encoding="utf-8"
        ).lower()
        forbidden = [
            "pypdf",
            "pdfreader",
            "pytesseract",
            "import ocr",
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
