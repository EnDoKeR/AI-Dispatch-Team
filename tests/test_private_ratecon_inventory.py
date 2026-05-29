import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import scripts.private_ratecon_inventory as inventory_cli
from scripts.private_ratecon_inventory import (
    build_private_ratecon_inventory,
    format_inventory,
)


SCRIPT_PATH = Path("scripts/private_ratecon_inventory.py")


class PrivateRateConInventoryTests(unittest.TestCase):
    def make_temp_files(self, folder):
        for file_name in [
            "realistic_private_name_one.pdf",
            "realistic_private_name_two.PDF",
            "manual_export.txt",
            "no_extension",
        ]:
            (folder / file_name).touch()

    def test_inventory_counts_files_and_extensions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_files(folder)

            report = build_private_ratecon_inventory(folder)

            self.assertEqual(report["total_files"], 4)
            self.assertEqual(report["extension_counts"][".pdf"], 2)
            self.assertEqual(report["extension_counts"][".txt"], 1)
            self.assertEqual(report["extension_counts"]["[no_extension]"], 1)

    def test_anonymized_labels_are_generated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_files(folder)

            report = build_private_ratecon_inventory(folder)
            labels = [item["label"] for item in report["labels"]]

            self.assertEqual(labels, ["RATECON_001", "RATECON_002", "RATECON_003", "RATECON_004"])

    def test_inventory_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_files(folder)

            report = build_private_ratecon_inventory(folder)

            json.dumps(report)

    def test_formatted_output_does_not_print_private_filenames(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_files(folder)

            report = build_private_ratecon_inventory(folder)
            text = format_inventory(report)

            self.assertIn("RATECON_001", text)
            self.assertIn("Total files: 4", text)
            self.assertNotIn("realistic_private_name_one", text)
            self.assertNotIn("realistic_private_name_two", text)
            self.assertNotIn("manual_export", text)

    def test_missing_directory_is_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"

            report = build_private_ratecon_inventory(missing)

            self.assertEqual(report["total_files"], 0)
            self.assertEqual(report["labels"], [])

    def test_cli_exists_and_prints_inventory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_files(folder)

            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--directory", str(folder)],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PRIVATE RATECON INVENTORY", result.stdout)
            self.assertIn("Total files: 4", result.stdout)
            self.assertIn("RATECON_001", result.stdout)
            self.assertNotIn("realistic_private_name_one", result.stdout)

    def test_cli_json_output_is_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.make_temp_files(folder)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--directory",
                    str(folder),
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            payload = json.loads(result.stdout)

            self.assertEqual(payload["total_files"], 4)
            self.assertEqual(payload["labels"][0]["label"], "RATECON_001")
            self.assertNotIn("realistic_private_name_one", result.stdout)

    def test_script_does_not_read_file_contents_or_import_forbidden_layers(self):
        source = inspect.getsource(inventory_cli).lower()
        forbidden = [
            "open(",
            "read_text",
            "read_bytes",
            "pypdf",
            "pytesseract",
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "gspread",
            "googlemaps",
            "dat_api",
            "gmail",
            "smtplib",
            "imaplib",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
