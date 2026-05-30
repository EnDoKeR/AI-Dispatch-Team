import csv
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from app.market_intelligence.intake import ratecon_value_review_csv_export
from app.market_intelligence.intake.ratecon_value_review_csv_export import (
    DEFAULT_VALUE_REVIEW_CSV_PATH,
    VALUE_REVIEW_COLUMNS,
    build_ratecon_value_review_csv_row,
    export_ratecon_value_review_csv,
)


FAKE_VALUE_SUMMARY = {
    "label": "RATECON_001",
    "parser_output": {
        "customer_name": "FAKE BROKER LLC",
        "load_label": "FAKE LOAD",
        "pickup_location": "Fake City, ST 00000",
        "pickup_date": "2026-05-30",
        "delivery_location": "Example City, ST 00000",
        "delivery_date": "2026-05-31",
        "load_number": "FAKE-REF-001",
        "rate": 2500,
        "commodity": "FAKE COMMODITY",
        "weight": 42000,
        "field_confidence": {
            "rate": "HIGH",
            "commodity": "LOW",
        },
    },
    "ratecon_core_summary": {
        "missing_core_fields": [],
        "optional_missing_fields": ["broker_mc", "equipment"],
        "deferred_fields": ["loaded_miles"],
        "loaded_miles": "",
        "miles_status": "DEFERRED_GOOGLE_MAPS",
        "miles_source": "NOT_FROM_RATECON",
    },
    "intake_summary": {
        "needs_check_fields": ["commodity"],
    },
    "result_category": "READY_FOR_REVIEW",
    "warnings": ["fake_warning"],
}


class RateConValueReviewCsvExportTests(unittest.TestCase):
    def test_builds_value_review_row(self):
        row = build_ratecon_value_review_csv_row(FAKE_VALUE_SUMMARY)

        self.assertEqual(row["anonymized_label"], "RATECON_001")
        self.assertEqual(row["customer_name"], "FAKE BROKER LLC")
        self.assertEqual(row["load_number"], "FAKE-REF-001")
        self.assertEqual(row["miles_status"], "DEFERRED_GOOGLE_MAPS")
        self.assertEqual(row["miles_source"], "NOT_FROM_RATECON")
        self.assertEqual(row["optional_missing_fields"], "broker_mc; equipment")
        self.assertEqual(row["deferred_fields"], "loaded_miles")
        self.assertEqual(row["low_confidence_fields"], "commodity")

    def test_exports_fake_summary_rows_to_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "value_review.csv"
            result = export_ratecon_value_review_csv(
                [FAKE_VALUE_SUMMARY],
                output_path=output_path,
            )

            with output_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(result["rows_written"], 1)
        self.assertEqual(rows[0]["anonymized_label"], "RATECON_001")
        self.assertEqual(rows[0]["customer_name"], "FAKE BROKER LLC")
        self.assertEqual(rows[0]["rate"], "2500")

    def test_exports_three_fake_summary_rows_to_csv(self):
        summaries = []

        for index in range(1, 4):
            summary = dict(FAKE_VALUE_SUMMARY)
            summary["label"] = f"RATECON_{index:03d}"
            summaries.append(summary)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "value_review.csv"
            result = export_ratecon_value_review_csv(
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
            output_path = Path(temp_dir) / "value_review.csv"
            export_ratecon_value_review_csv(
                [FAKE_VALUE_SUMMARY],
                output_path=output_path,
            )

            with output_path.open(newline="", encoding="utf-8") as handle:
                header = handle.readline().strip().split(",")

        self.assertEqual(header, VALUE_REVIEW_COLUMNS)

    def test_default_output_path_is_private_ignored_folder(self):
        self.assertEqual(
            DEFAULT_VALUE_REVIEW_CSV_PATH.as_posix(),
            "data/private_ratecons/dry_run_results/ratecon_value_review.csv",
        )

    def test_no_raw_text_columns(self):
        forbidden_columns = {
            "raw_text",
            "extracted_text",
            "private_text",
            "document_text",
            "snippet",
        }

        self.assertTrue(forbidden_columns.isdisjoint(set(VALUE_REVIEW_COLUMNS)))

    def test_export_metadata_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = export_ratecon_value_review_csv(
                [FAKE_VALUE_SUMMARY],
                output_path=Path(temp_dir) / "value_review.csv",
            )

        json.dumps(result)
        self.assertFalse(result["raw_text_saved"])
        self.assertFalse(result["private_text_saved"])
        self.assertFalse(result["google_sheets_used"])

    def test_no_forbidden_imports(self):
        source = inspect.getsource(ratecon_value_review_csv_export).lower()
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
