import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import scripts.run_private_ratecon_pdf_extraction_inventory as inventory_cli
from scripts.run_private_ratecon_pdf_extraction_inventory import (
    build_private_pdf_extraction_inventory,
    format_private_pdf_extraction_inventory,
)


SCRIPT_PATH = Path("scripts/run_private_ratecon_pdf_extraction_inventory.py")
RAW_TEXT = "PRIVATE RAW TEXT SHOULD NEVER PRINT"


def fake_extractor(_path):
    return {
        "text": RAW_TEXT,
        "extractor_name": "fake",
        "page_count": 2,
        "char_count": len(RAW_TEXT),
        "extraction_status": "TEXT_EXTRACTED",
        "warnings": [],
        "private_text_saved": False,
    }


class PrivateRateConPdfExtractionInventoryTests(unittest.TestCase):
    def make_temp_files(self, folder):
        for file_name in [
            "private_alpha.pdf",
            "private_beta.PDF",
            "private_gamma.pdf",
            "ignore_text_export.txt",
        ]:
            (folder / file_name).touch()

    def test_inventory_uses_anonymized_labels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_files(folder)

            report = build_private_pdf_extraction_inventory(
                directory=folder,
                limit=2,
                extractor=fake_extractor,
            )

        self.assertEqual(report["total_pdf_files"], 3)
        self.assertEqual(report["processed_count"], 2)
        self.assertEqual(
            [item["label"] for item in report["results"]],
            ["RATECON_001", "RATECON_002"],
        )

    def test_inventory_does_not_include_raw_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_files(folder)

            report = build_private_pdf_extraction_inventory(
                directory=folder,
                limit=1,
                extractor=fake_extractor,
            )
            formatted = format_private_pdf_extraction_inventory(report)

        self.assertNotIn("text", report["results"][0])
        self.assertNotIn(RAW_TEXT, json.dumps(report))
        self.assertNotIn(RAW_TEXT, formatted)
        self.assertNotIn("private_alpha", formatted)

    def test_limit_behavior(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_files(folder)

            report = build_private_pdf_extraction_inventory(
                directory=folder,
                limit=1,
                extractor=fake_extractor,
            )

        self.assertEqual(report["processed_count"], 1)
        self.assertEqual(report["limit"], 1)

    def test_missing_folder_is_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"

            report = build_private_pdf_extraction_inventory(
                directory=missing,
                extractor=fake_extractor,
            )

        self.assertEqual(report["total_pdf_files"], 0)
        self.assertEqual(report["processed_count"], 0)
        self.assertEqual(report["results"], [])

    def test_report_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_files(folder)

            report = build_private_pdf_extraction_inventory(
                directory=folder,
                limit=1,
                extractor=fake_extractor,
            )

        json.dumps(report)

    def test_cli_exists_and_prints_safe_inventory(self):
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
        self.assertIn("PRIVATE RATECON PDF EXTRACTION INVENTORY", result.stdout)
        self.assertIn("RATECON_001", result.stdout)
        self.assertIn("DRY RUN ONLY", result.stdout)
        self.assertNotIn("invalid_private", result.stdout)

    def test_script_has_no_forbidden_imports_or_preview_option(self):
        source = inspect.getsource(inventory_cli).lower()
        forbidden = [
            "--show-preview",
            "read_text",
            "read_bytes",
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
