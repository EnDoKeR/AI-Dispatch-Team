import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import scripts.run_private_ratecon_pdf_dry_run as pdf_cli
from scripts.run_private_ratecon_pdf_dry_run import (
    build_private_pdf_dry_run_report,
    format_private_pdf_dry_run_report,
)


SCRIPT_PATH = Path("scripts/run_private_ratecon_pdf_dry_run.py")
RAW_VALUE = "PRIVATE RAW VALUE SHOULD NOT PRINT"


def fake_runner(_path, anonymized_label=""):
    return {
        "anonymized_label": anonymized_label,
        "extraction_status": "TEXT_EXTRACTED",
        "extraction_metadata": {
            "extractor_name": "fake",
            "page_count": 1,
            "char_count": 123,
            "extraction_status": "TEXT_EXTRACTED",
            "warnings": [],
            "private_text_saved": False,
        },
        "dry_run_result": {
            "parser_output": {
                "broker_name": RAW_VALUE,
                "field_confidence": {
                    "broker_name": "LOW",
                    "rate": "HIGH",
                },
            },
            "intake_summary": {
                "missing_fields": ["broker_mc"],
                "needs_check_fields": ["broker_name"],
            },
            "ratecon_core_summary": {
                "core_fields_present": True,
                "missing_core_fields": [],
                "optional_missing_fields": ["broker_mc", "equipment"],
                "deferred_fields": ["loaded_miles"],
                "miles_status": "DEFERRED_GOOGLE_MAPS",
                "miles_source": "NOT_FROM_RATECON",
            },
            "link_candidate": {
                "recommended_action": "NEEDS_REVIEW",
            },
            "status": "READY_FOR_REVIEW",
        },
        "status": "READY_FOR_REVIEW",
        "warnings": ["text_dry_run:low_confidence_broker_name"],
        "private_text_saved": False,
        "cases_created": False,
        "events_written": False,
    }


class PrivateRateConPdfDryRunCliTests(unittest.TestCase):
    def make_temp_pdfs(self, folder):
        for file_name in [
            "private_alpha.pdf",
            "private_beta.PDF",
            "ignored.txt",
        ]:
            (folder / file_name).touch()

    def test_report_respects_limit_and_uses_anonymized_labels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_pdfs(folder)

            report = build_private_pdf_dry_run_report(
                directory=folder,
                limit=1,
                runner=fake_runner,
            )

        self.assertEqual(report["total_pdf_files"], 2)
        self.assertEqual(report["processed_count"], 1)
        self.assertEqual(report["results"][0]["label"], "RATECON_001")

    def test_report_does_not_include_raw_private_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_pdfs(folder)

            report = build_private_pdf_dry_run_report(
                directory=folder,
                limit=1,
                runner=fake_runner,
            )
            text = format_private_pdf_dry_run_report(report)

        self.assertNotIn(RAW_VALUE, json.dumps(report))
        self.assertNotIn(RAW_VALUE, text)
        self.assertNotIn("private_alpha", text)
        self.assertIn("broker_mc", text)
        self.assertIn("broker_name", text)
        self.assertIn("missing_core_fields", text)
        self.assertIn("optional_missing_fields", text)
        self.assertIn("DEFERRED_GOOGLE_MAPS", text)

    def test_report_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_pdfs(folder)

            report = build_private_pdf_dry_run_report(
                directory=folder,
                limit=1,
                runner=fake_runner,
            )

        json.dumps(report)

    def test_missing_folder_is_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"

            report = build_private_pdf_dry_run_report(
                directory=missing,
                runner=fake_runner,
            )

        self.assertEqual(report["total_pdf_files"], 0)
        self.assertEqual(report["processed_count"], 0)

    def test_cli_exists_and_prints_safe_summary(self):
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
        self.assertIn("PRIVATE RATECON PDF DRY-RUN REPORT", result.stdout)
        self.assertIn("RATECON_001", result.stdout)
        self.assertIn("DRY RUN ONLY", result.stdout)
        self.assertNotIn("invalid_private", result.stdout)

    def test_cli_has_no_forbidden_imports_or_file_output(self):
        source = inspect.getsource(pdf_cli).lower()
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
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
