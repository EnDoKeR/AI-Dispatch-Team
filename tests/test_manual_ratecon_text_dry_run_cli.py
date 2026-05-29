import inspect
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.run_manual_ratecon_text_dry_run as manual_cli


SCRIPT_PATH = Path("scripts/run_manual_ratecon_text_dry_run.py")


class ManualRateConTextDryRunCliTests(unittest.TestCase):
    def test_cli_sample_mode_works(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MANUAL RATECON TEXT DRY RUN", result.stdout)
        self.assertIn("Input mode: sample", result.stdout)
        self.assertIn("Synthetic Manual Broker", result.stdout)
        self.assertIn("Link candidate:", result.stdout)

    def test_cli_text_argument_works(self):
        text = (
            "Broker: Synthetic Text Broker\n"
            "Broker MC: 000777\n"
            "Rate: 3100\n"
            "Pickup: Dallas, TX\n"
            "Pickup Date: 2026-09-01\n"
            "Delivery: Denver, CO\n"
            "Delivery Date: 2026-09-03\n"
            "Commodity: Synthetic steel\n"
            "Weight: 40000\n"
            "Reference: SYN-TEXT-001\n"
            "Equipment: Conestoga\n"
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--text", text],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Input mode: manual text", result.stdout)
        self.assertIn("Synthetic Text Broker", result.stdout)
        self.assertIn("Status: READY_FOR_REVIEW", result.stdout)

    def test_cli_stdin_mode_works(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--stdin"],
            input="Broker: Synthetic Stdin Broker\n",
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Input mode: stdin", result.stdout)
        self.assertIn("Synthetic Stdin Broker", result.stdout)

    def test_empty_text_is_handled_safely(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--text", ""],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Status: MISSING_FIELDS", result.stdout)
        self.assertIn("Warnings: empty_text", result.stdout)

    def test_output_includes_dry_run_warning(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(
            "DRY RUN ONLY - no private text saved, no cases linked or created",
            result.stdout,
        )
        self.assertIn("Private text saved: False", result.stdout)
        self.assertIn("Cases created: False", result.stdout)
        self.assertIn("Events written: False", result.stdout)

    def test_cli_has_no_file_reading_option_or_runtime_reads(self):
        source = inspect.getsource(manual_cli).lower()

        self.assertNotIn("--file", source)
        self.assertNotIn("--pdf", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("read_text", source)
        self.assertNotIn("read_bytes", source)
        self.assertNotIn("private_ratecons", source)
        self.assertNotIn("data/", source)
        self.assertNotIn("jsonl", source)

    def test_cli_has_no_forbidden_imports(self):
        source = inspect.getsource(manual_cli).lower()
        forbidden = [
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "telegram_sender",
            "telegram_notifier",
            "pypdf",
            "pytesseract",
            "gspread",
            "google.oauth",
            "googlemaps",
            "dat_api",
            "load_intake",
            "scheduler",
            "threading",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
