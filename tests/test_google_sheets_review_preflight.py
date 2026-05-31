import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.document_ai.ratecon_review_workbook import (
    DOCUMENT_SUMMARY_COLUMNS,
    FIELD_REVIEW_COLUMNS,
    RATE_REVIEW_COLUMNS,
    REVIEW_DOCUMENT_SUMMARY_CSV,
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_RATE_REVIEW_CSV,
    REVIEW_STOP_REVIEW_CSV,
    STOP_REVIEW_COLUMNS,
)
from app.integrations.google_sheets_review_preflight import (
    preflight_google_review_outputs,
)
from scripts import sync_ratecon_review_to_google_sheet as sync_script


def _write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _write_all_review_csvs(root, extra_stop_columns=None):
    _write_csv(
        root / REVIEW_DOCUMENT_SUMMARY_CSV,
        DOCUMENT_SUMMARY_COLUMNS,
        [{"Measurement Alias": "RATECON_001", "Readiness Level": "review"}],
    )
    _write_csv(
        root / REVIEW_STOP_REVIEW_CSV,
        list(STOP_REVIEW_COLUMNS) + list(extra_stop_columns or []),
        [
            {
                "Measurement Alias": "RATECON_001",
                "Stop ID": "span_stop_001",
                "Field Name": "location",
                "Predicted Value LOCAL ONLY": "Fake Private Stop Value",
            }
        ],
    )
    _write_csv(
        root / REVIEW_FIELD_REVIEW_CSV,
        FIELD_REVIEW_COLUMNS,
        [{"Measurement Alias": "RATECON_001", "Field Name": "rate"}],
    )
    _write_csv(
        root / REVIEW_RATE_REVIEW_CSV,
        RATE_REVIEW_COLUMNS,
        [{"Measurement Alias": "RATECON_001", "Rate Field Type": "rate"}],
    )


class GoogleSheetsReviewPreflightTests(unittest.TestCase):
    def test_preflight_passes_fake_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_all_review_csvs(root)

            result = preflight_google_review_outputs(root)

        self.assertTrue(result["review_outputs_found"])
        self.assertTrue(result["headers_valid"])
        self.assertTrue(result["sync_ready"])
        self.assertEqual(result["rows_per_source_file"][REVIEW_STOP_REVIEW_CSV], 1)
        self.assertFalse(result["private_values_printed"])

    def test_preflight_reports_missing_output_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(
                root / REVIEW_DOCUMENT_SUMMARY_CSV,
                DOCUMENT_SUMMARY_COLUMNS,
                [{"Measurement Alias": "RATECON_001"}],
            )

            result = preflight_google_review_outputs(root)

        self.assertFalse(result["sync_ready"])
        self.assertIn(REVIEW_STOP_REVIEW_CSV, result["missing_csv_basenames"])
        self.assertIn("missing_review_csv", result["warning_codes"])

    def test_preflight_reports_bad_header_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_all_review_csvs(root)
            _write_csv(
                root / REVIEW_FIELD_REVIEW_CSV,
                ["Measurement Alias", "Wrong Header"],
                [{"Measurement Alias": "RATECON_001"}],
            )

            result = preflight_google_review_outputs(root)

        self.assertFalse(result["headers_valid"])
        self.assertIn("invalid_review_csv_headers", result["warning_codes"])
        self.assertNotIn("Fake Private", str(result))

    def test_preflight_blocks_raw_text_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_all_review_csvs(root, extra_stop_columns=["Raw Text"])

            result = preflight_google_review_outputs(root)

        self.assertFalse(result["sync_ready"])
        self.assertTrue(result["raw_text_columns_found"])
        self.assertIn("raw_text_column_found", result["warning_codes"])

    def test_sync_script_preflight_only_does_not_require_confirm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_all_review_csvs(root)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = sync_script.main(
                    ["--input-dir", tmp, "--preflight-only"]
                )
            output = stdout.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("sync_ready: True", output)
        self.assertIn(REVIEW_STOP_REVIEW_CSV, output)
        self.assertNotIn("Fake Private", output)
        self.assertNotIn(tmp, output)


if __name__ == "__main__":
    unittest.main()
