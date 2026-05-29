import contextlib
import io
from pathlib import Path
import unittest

from scripts import run_pasted_text_parser_dry_run


class PastedTextParserCliTests(unittest.TestCase):
    def test_cli_works_with_text_argument(self):
        text = (
            "Broker: Synthetic CLI Test Broker\n"
            "Broker MC: SYNTH-MC-CLI-TEST\n"
            "Rate: 3100\n"
            "Pickup: Dallas, TX\n"
            "Pickup Date: 2026-08-01\n"
            "Delivery: Denver, CO\n"
            "Delivery Date: 2026-08-02\n"
            "Commodity: Synthetic steel\n"
            "Weight: 40000\n"
            "Reference: SYNTH-CLI-TEST-001\n"
            "Equipment: Conestoga\n"
        )
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = run_pasted_text_parser_dry_run.main(["--text", text])

        self.assertEqual(result, 0)
        self.assertIn("PASTED TEXT PARSER DRY RUN", output.getvalue())
        self.assertIn("Synthetic CLI Test Broker", output.getvalue())
        self.assertIn("Status: READY_FOR_REVIEW", output.getvalue())

    def test_cli_works_with_sample_mode(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = run_pasted_text_parser_dry_run.main([])

        text = output.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("Input mode: sample", text)
        self.assertIn("Synthetic CLI Broker", text)

    def test_empty_text_is_handled_safely(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = run_pasted_text_parser_dry_run.main(["--text", ""])

        text = output.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("Status: MISSING_FIELDS", text)
        self.assertIn("Missing fields:", text)
        self.assertIn("Broker: MISSING", text)

    def test_output_includes_dry_run_warning_and_confidence(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            run_pasted_text_parser_dry_run.main([])

        text = output.getvalue()

        self.assertIn(
            "DRY RUN ONLY - pasted text only, no PDF/OCR/private file processing",
            text,
        )
        self.assertIn("Field confidence:", text)
        self.assertIn("Missing fields:", text)
        self.assertIn("Needs-check fields:", text)

    def test_cli_script_has_no_file_reading_or_forbidden_imports(self):
        source = Path("scripts/run_pasted_text_parser_dry_run.py").read_text(
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
            "private_ratecons",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
