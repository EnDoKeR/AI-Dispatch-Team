import csv
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from app.market_intelligence.intake import ratecon_dry_run_csv_export
from app.market_intelligence.intake.ratecon_dry_run_csv_export import (
    CSV_COLUMNS,
    build_ratecon_dry_run_csv_row,
    export_ratecon_dry_run_csv,
)


SAFE_SUMMARY = {
    "label": "RATECON_001",
    "extraction_status": "TEXT_EXTRACTED",
    "page_count": 2,
    "char_count": 2828,
    "intake_status": "MISSING_FIELDS",
    "result_category": "NEEDS_PARSER_FIX",
    "missing_fields": ["broker_mc", "weight"],
    "needs_check_fields": ["broker_mc"],
    "low_confidence_fields": ["rate"],
    "suspected_parser_gap_fields": ["broker_mc", "weight"],
    "link_candidate_action": "NEEDS_REVIEW",
    "approval_required": True,
    "warnings": ["sample_warning"],
}


class RateConDryRunCsvExportTests(unittest.TestCase):
    def test_builds_safe_csv_row(self):
        row = build_ratecon_dry_run_csv_row(SAFE_SUMMARY)

        self.assertEqual(row["anonymized_label"], "RATECON_001")
        self.assertEqual(row["broker_mc_status"], "missing")
        self.assertEqual(row["rate_status"], "low_confidence")
        self.assertEqual(row["weight_status"], "missing")
        self.assertEqual(row["approval_required"], "yes")

    def test_exports_fake_summary_rows_to_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "dry_run.csv"
            result = export_ratecon_dry_run_csv(
                [SAFE_SUMMARY],
                output_path=output_path,
            )

            with output_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(result["rows_written"], 1)
        self.assertEqual(rows[0]["anonymized_label"], "RATECON_001")
        self.assertEqual(rows[0]["missing_fields"], "broker_mc; weight")

    def test_exports_three_fake_summary_rows_to_csv(self):
        summaries = []

        for index in range(1, 4):
            summary = dict(SAFE_SUMMARY)
            summary["label"] = f"RATECON_{index:03d}"
            summaries.append(summary)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "dry_run.csv"
            result = export_ratecon_dry_run_csv(
                summaries,
                output_path=output_path,
            )

            with output_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(result["rows_written"], 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            [row["anonymized_label"] for row in rows],
            ["RATECON_001", "RATECON_002", "RATECON_003"],
        )

    def test_field_ordering_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "dry_run.csv"
            export_ratecon_dry_run_csv(
                [SAFE_SUMMARY],
                output_path=output_path,
            )

            with output_path.open(newline="", encoding="utf-8") as handle:
                header = handle.readline().strip().split(",")

        self.assertEqual(header, CSV_COLUMNS)

    def test_no_raw_text_columns(self):
        forbidden_columns = {
            "raw_text",
            "extracted_text",
            "private_text",
            "broker_name",
            "broker_mc",
            "reference_id",
            "pickup_location",
            "delivery_location",
        }

        self.assertTrue(forbidden_columns.isdisjoint(set(CSV_COLUMNS)))

    def test_export_metadata_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = export_ratecon_dry_run_csv(
                [SAFE_SUMMARY],
                output_path=Path(temp_dir) / "dry_run.csv",
            )

        json.dumps(result)
        self.assertFalse(result["raw_text_saved"])
        self.assertFalse(result["private_text_saved"])
        self.assertFalse(result["google_sheets_used"])

    def test_no_forbidden_imports(self):
        source = inspect.getsource(ratecon_dry_run_csv_export).lower()
        forbidden = [
            "gspread",
            "google.",
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
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
