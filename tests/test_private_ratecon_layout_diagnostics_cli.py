import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import scripts.run_private_ratecon_layout_diagnostics as layout_cli
from scripts.run_private_ratecon_layout_diagnostics import (
    build_private_ratecon_layout_diagnostics_report,
    format_private_ratecon_layout_diagnostics_report,
)


SCRIPT_PATH = Path("scripts/run_private_ratecon_layout_diagnostics.py")
RAW_VALUE = "PRIVATE RAW FIELD VALUE SHOULD NOT PRINT"


def fake_extractor(_path):
    return {
        "text": (
            f"Broker Name: {RAW_VALUE}\n"
            "Broker MC: MC000000\n"
            "TOTAL: USD $0000.00\n"
            "Load #: FAKE-REF-001\n"
            "Shipper Information:\n"
            "Address: Fake City, ST 00000\n"
            "Consignee Information:\n"
            "Address: Fake Town, ST 00000\n"
            "Total Weight: 40000 LBS\n"
        ),
        "extractor_name": "fake",
        "page_count": 2,
        "char_count": 222,
        "extraction_status": "TEXT_EXTRACTED",
        "warnings": [],
        "private_text_saved": False,
    }


class PrivateRateConLayoutDiagnosticsCliTests(unittest.TestCase):
    def make_temp_pdfs(self, folder):
        for file_name in ["private_alpha.pdf", "private_beta.PDF", "ignored.txt"]:
            (folder / file_name).touch()

    def test_report_respects_limit_and_anonymized_labels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_pdfs(folder)
            report = build_private_ratecon_layout_diagnostics_report(
                directory=folder,
                limit=1,
                extractor=fake_extractor,
            )

        self.assertEqual(report["total_pdf_files"], 2)
        self.assertEqual(report["processed_count"], 1)
        self.assertEqual(report["results"][0]["label"], "RATECON_001")

    def test_placeholder_shapes_are_reported_without_raw_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_pdfs(folder)
            report = build_private_ratecon_layout_diagnostics_report(
                directory=folder,
                limit=1,
                extractor=fake_extractor,
            )
            formatted = format_private_ratecon_layout_diagnostics_report(report)
            serialized = json.dumps(report)

        self.assertIn("<AMOUNT>", formatted)
        self.assertIn("<ID>", formatted)
        self.assertIn("<LOCATION>", formatted)
        self.assertIn("<WEIGHT>", formatted)
        self.assertNotIn(RAW_VALUE, formatted)
        self.assertNotIn(RAW_VALUE, serialized)
        self.assertNotIn("MC000000", formatted)
        self.assertNotIn("FAKE-REF-001", formatted)
        self.assertNotIn("Fake City", formatted)
        self.assertNotIn("Fake Town", formatted)

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
        self.assertIn("PRIVATE RATECON REDACTED LAYOUT DIAGNOSTICS", result.stdout)
        self.assertIn("DRY RUN ONLY - redacted layout diagnostics", result.stdout)
        self.assertIn("RATECON_001", result.stdout)
        self.assertNotIn("invalid_private", result.stdout)

    def test_report_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_pdfs(folder)
            report = build_private_ratecon_layout_diagnostics_report(
                directory=folder,
                limit=1,
                extractor=fake_extractor,
            )

        json.dumps(report)

    def test_no_forbidden_imports_or_file_output(self):
        source = inspect.getsource(layout_cli).lower()
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
