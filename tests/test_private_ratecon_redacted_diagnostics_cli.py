import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import scripts.run_private_ratecon_redacted_diagnostics as diagnostics_cli
from scripts.run_private_ratecon_redacted_diagnostics import (
    build_private_ratecon_redacted_diagnostics_report,
    format_private_ratecon_redacted_diagnostics_report,
)


SCRIPT_PATH = Path("scripts/run_private_ratecon_redacted_diagnostics.py")
RAW_VALUE = "PRIVATE RAW FIELD VALUE SHOULD NOT PRINT"


def fake_extractor(_path):
    return {
        "text": (
            f"Broker: {RAW_VALUE}\n"
            "Motor Carrier: 000000\n"
            "Rate: 3000\n"
            "Pickup Date: hidden\n"
            "Pickup: hidden\n"
            "Delivery: hidden\n"
            "Reference: hidden\n"
            "Detention: hidden\n"
        ),
        "extractor_name": "fake",
        "page_count": 2,
        "char_count": 222,
        "extraction_status": "TEXT_EXTRACTED",
        "warnings": [],
        "private_text_saved": False,
    }


class PrivateRateConRedactedDiagnosticsCliTests(unittest.TestCase):
    def make_temp_pdfs(self, folder):
        for file_name in [
            "private_alpha.pdf",
            "private_beta.PDF",
            "ignored.txt",
        ]:
            (folder / file_name).touch()

    def test_report_respects_limit_and_anonymized_labels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_pdfs(folder)

            report = build_private_ratecon_redacted_diagnostics_report(
                directory=folder,
                limit=1,
                extractor=fake_extractor,
            )

        self.assertEqual(report["total_pdf_files"], 2)
        self.assertEqual(report["processed_count"], 1)
        self.assertEqual(report["results"][0]["label"], "RATECON_001")

    def test_signal_counts_and_parser_gap_fields_are_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_pdfs(folder)

            report = build_private_ratecon_redacted_diagnostics_report(
                directory=folder,
                limit=1,
                extractor=fake_extractor,
            )
            item = report["results"][0]

        self.assertGreater(item["signal_counts"]["broker_mc"], 0)
        self.assertIn("broker_mc", item["suspected_parser_gap_fields"])
        self.assertIn("rate", item["extracted_field_status"])

    def test_formatted_output_does_not_include_raw_text_or_filenames(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_pdfs(folder)

            report = build_private_ratecon_redacted_diagnostics_report(
                directory=folder,
                limit=1,
                extractor=fake_extractor,
            )
            formatted = format_private_ratecon_redacted_diagnostics_report(report)

        self.assertNotIn(RAW_VALUE, json.dumps(report))
        self.assertNotIn(RAW_VALUE, formatted)
        self.assertNotIn("private_alpha", formatted)
        self.assertIn("signal_counts:", formatted)
        self.assertIn("suspected_parser_gap_fields:", formatted)

    def test_report_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_pdfs(folder)

            report = build_private_ratecon_redacted_diagnostics_report(
                directory=folder,
                limit=1,
                extractor=fake_extractor,
            )

        json.dumps(report)

    def test_missing_folder_is_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"

            report = build_private_ratecon_redacted_diagnostics_report(
                directory=missing,
                extractor=fake_extractor,
            )

        self.assertEqual(report["total_pdf_files"], 0)
        self.assertEqual(report["processed_count"], 0)
        self.assertEqual(report["results"], [])

    def test_cli_exists_and_prints_dry_run_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            (folder / "invalid_private.pdf").write_bytes(b"not a real pdf")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--directory",
                    str(folder),
                    "--limit",
                    "1",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PRIVATE RATECON REDACTED DIAGNOSTICS", result.stdout)
        self.assertIn("DRY RUN ONLY - redacted diagnostics", result.stdout)
        self.assertIn("RATECON_001", result.stdout)
        self.assertNotIn("invalid_private", result.stdout)

    def test_no_forbidden_imports_or_file_output(self):
        source = inspect.getsource(diagnostics_cli).lower()
        forbidden = [
            "read_text",
            "read_bytes",
            "write_text",
            "write_bytes",
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "pytesseract",
            "easyocr",
            "gspread",
            "gmail",
            "smtplib",
            "imaplib",
            "googlemaps",
            "dat_api",
            "load_intake",
            "--show-preview",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
