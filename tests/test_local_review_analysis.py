import csv
import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.local_review_analysis import (
    LOCAL_REVIEW_ISSUE_BROKER_IDENTITY_MISSING,
    LOCAL_REVIEW_ISSUE_MISSING_STOP_DATE,
    LOCAL_REVIEW_ISSUE_MISSING_STOP_TIME,
    LOCAL_REVIEW_ISSUE_OCR_NEEDED,
    LocalReviewAnalysisError,
    analyze_local_review_outputs,
    build_local_review_analysis,
    load_document_summary_csv,
)
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


def _write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _write_fake_review_outputs(root):
    _write_csv(
        root / REVIEW_DOCUMENT_SUMMARY_CSV,
        DOCUMENT_SUMMARY_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Readiness Level": "extraction_review_ready",
                "Extraction Relevant": "yes",
                "Normal Load Movement": "yes",
                "OCR Needed": "no",
                "Old Normalized Stops": "8",
                "Span Normalized Stops": "2",
                "Date Missing": "2",
                "Time Missing": "1",
                "Review Required Stops": "2",
            },
            {
                "Measurement Alias": "RATECON_002",
                "Readiness Level": "not_ready",
                "OCR Needed": "yes",
            },
        ],
    )
    _write_csv(
        root / REVIEW_STOP_REVIEW_CSV,
        STOP_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Stop ID": "span_stop_001",
                "Stop Type": "pickup",
                "Field Name": "date",
                "Predicted Value LOCAL ONLY": "Fake Private Date",
                "Status": "missing",
                "Needs Review": "yes",
            },
            {
                "Measurement Alias": "RATECON_001",
                "Stop ID": "span_stop_001",
                "Stop Type": "pickup",
                "Field Name": "time",
                "Predicted Value LOCAL ONLY": "Fake Private Time",
                "Status": "missing",
                "Needs Review": "yes",
            },
        ],
    )
    _write_csv(
        root / REVIEW_FIELD_REVIEW_CSV,
        FIELD_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "broker_name",
                "Predicted Value LOCAL ONLY": "Fake Broker",
                "Status": "missing",
                "Needs Review": "yes",
            },
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "rate",
                "Predicted Value LOCAL ONLY": "Fake Rate",
                "Status": "conflict",
                "Needs Review": "yes",
            },
        ],
    )
    _write_csv(
        root / REVIEW_RATE_REVIEW_CSV,
        RATE_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Rate Field Type": "rate",
                "Predicted Value LOCAL ONLY": "Fake Rate",
                "Status": "resolved",
            }
        ],
    )


class LocalReviewAnalysisTests(unittest.TestCase):
    def test_builds_issue_category_summary_without_values(self):
        analysis = build_local_review_analysis(
            document_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Readiness Level": "extraction_review_ready",
                    "Date Missing": "2",
                    "Time Missing": "1",
                }
            ],
            stop_rows=[],
            field_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": "broker_name",
                    "Status": "missing",
                    "Predicted Value LOCAL ONLY": "Fake Broker",
                }
            ],
            rate_rows=[],
        )

        alias = analysis["aliases"][0]
        self.assertIn(LOCAL_REVIEW_ISSUE_MISSING_STOP_DATE, alias["issue_categories"])
        self.assertIn(
            LOCAL_REVIEW_ISSUE_BROKER_IDENTITY_MISSING,
            alias["issue_categories"],
        )
        payload = json.dumps(analysis)
        self.assertNotIn("Fake Broker", payload)
        self.assertFalse(analysis["private_values_included"])

    def test_aggregate_counts_and_top_blocker_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_review_outputs(root)

            analysis = analyze_local_review_outputs(root)

        aggregate = analysis["aggregate"]
        self.assertEqual(aggregate["document_count"], 2)
        self.assertEqual(aggregate["ocr_needed_count"], 1)
        self.assertIn(LOCAL_REVIEW_ISSUE_MISSING_STOP_DATE, aggregate["issue_category_counts"])
        self.assertIn(LOCAL_REVIEW_ISSUE_MISSING_STOP_TIME, aggregate["issue_category_counts"])
        self.assertIn(LOCAL_REVIEW_ISSUE_OCR_NEEDED, aggregate["issue_category_counts"])
        self.assertIn("broker_name", aggregate["field_issue_counts"])
        self.assertIn("date", aggregate["stop_issue_counts"])

    def test_missing_csv_returns_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LocalReviewAnalysisError) as ctx:
                analyze_local_review_outputs(tmp)

        self.assertIn("review CSV missing", str(ctx.exception))

    def test_stale_header_returns_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(
                root / REVIEW_DOCUMENT_SUMMARY_CSV,
                ["Measurement Alias"],
                [{"Measurement Alias": "RATECON_001"}],
            )

            with self.assertRaises(LocalReviewAnalysisError) as ctx:
                load_document_summary_csv(root / REVIEW_DOCUMENT_SUMMARY_CSV)

        self.assertIn("stale or invalid", str(ctx.exception))

    def test_local_document_names_are_optional_local_only(self):
        analysis = build_local_review_analysis(
            document_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Local Document Name / File Stem": "FakeLocalName",
                }
            ],
            stop_rows=[],
            field_rows=[],
            rate_rows=[],
            include_local_document_names=False,
        )
        self.assertNotIn("local_document_name", analysis["aliases"][0])

        with_name = build_local_review_analysis(
            document_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Local Document Name / File Stem": "FakeLocalName",
                }
            ],
            stop_rows=[],
            field_rows=[],
            rate_rows=[],
            include_local_document_names=True,
        )
        self.assertEqual(with_name["aliases"][0]["local_document_name"], "FakeLocalName")


if __name__ == "__main__":
    unittest.main()
