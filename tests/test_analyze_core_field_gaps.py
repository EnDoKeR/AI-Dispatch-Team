import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.document_ai.core_field_gap_analysis import (
    CORE_FIELD_GAP_ANALYSIS_JSON,
    CORE_FIELD_GAP_ANALYSIS_MD,
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
from scripts import analyze_core_field_gaps as cli


def _write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _write_fake_outputs(root):
    _write_csv(
        root / REVIEW_DOCUMENT_SUMMARY_CSV,
        DOCUMENT_SUMMARY_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Readiness Level": "extraction_review_ready",
                "OCR Needed": "no",
            }
        ],
    )
    _write_csv(
        root / REVIEW_STOP_REVIEW_CSV,
        STOP_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Stop Type": "pickup",
                "Field Name": "date",
                "Status": "missing",
            }
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
            },
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "rate",
                "Predicted Value LOCAL ONLY": "Fake Rate",
                "Status": "conflict",
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
                "Status": "conflict",
            }
        ],
    )
    (root / "safe_summary.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "document_alias": "RATECON_001",
                        "field_statuses": [
                            {
                                "field_name": "broker_name",
                                "status": "missing",
                                "candidate_count": 0,
                                "confidence_bucket": "none",
                            },
                            {
                                "field_name": "rate",
                                "status": "conflict",
                                "candidate_count": 2,
                                "confidence_bucket": "high",
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


class AnalyzeCoreFieldGapsCliTests(unittest.TestCase):
    def test_cli_writes_reports_and_console_is_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_outputs(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(
                    [
                        "--input-dir",
                        str(root),
                        "--write-md",
                        "--write-json",
                    ]
                )

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertIn("documents_analyzed: 1", output)
            self.assertIn("recommended_next_target", output)
            self.assertIn("private_values_printed: False", output)
            self.assertNotIn("Fake Broker", output)
            self.assertTrue((root / CORE_FIELD_GAP_ANALYSIS_MD).exists())
            self.assertTrue((root / CORE_FIELD_GAP_ANALYSIS_JSON).exists())
            payload = (root / CORE_FIELD_GAP_ANALYSIS_JSON).read_text(encoding="utf-8")
            self.assertNotIn("Fake Rate", payload)

    def test_cli_missing_output_returns_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", tmp])

        self.assertEqual(result, 2)
        self.assertIn("core_field_gap_analysis_error", stdout.getvalue())

    def test_cli_can_omit_alias_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_outputs(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(
                    [
                        "--input-dir",
                        str(root),
                        "--no-console-alias-details",
                    ]
                )

        self.assertEqual(result, 0)
        self.assertNotIn("aliases_for_", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
