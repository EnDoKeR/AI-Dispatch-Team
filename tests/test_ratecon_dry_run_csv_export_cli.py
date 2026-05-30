import csv
import inspect
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import scripts.export_ratecon_dry_run_csv as export_cli


SCRIPT_PATH = Path("scripts/export_ratecon_dry_run_csv.py")


class RateConDryRunCsvExportCliTests(unittest.TestCase):
    def test_cli_default_limit_is_batch_three(self):
        parser = export_cli.build_parser()
        args = parser.parse_args([])

        self.assertEqual(args.limit, 3)

    def test_cli_sample_mode_writes_csv_and_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "sample.csv"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--sample",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            with output_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RATECON DRY-RUN CSV EXPORT", result.stdout)
        self.assertIn("DRY RUN ONLY", result.stdout)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["anonymized_label"], "RATECON_001")

    def test_cli_source_has_no_forbidden_integrations(self):
        source = inspect.getsource(export_cli).lower()
        forbidden = [
            "gspread",
            "google.oauth",
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "gmail",
            "googlemaps",
            "dat_api",
            "load_intake",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
