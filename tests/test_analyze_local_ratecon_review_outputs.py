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
from scripts import analyze_local_ratecon_review_outputs as cli


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
                "Date Missing": "1",
                "Time Missing": "1",
                "Review Required Stops": "1",
            }
        ],
    )
    _write_csv(
        root / REVIEW_STOP_REVIEW_CSV,
        STOP_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "date",
                "Predicted Value LOCAL ONLY": "Fake Private Date",
                "Status": "missing",
                "Needs Review": "yes",
            }
        ],
    )
    _write_csv(
        root / REVIEW_FIELD_REVIEW_CSV,
        FIELD_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "pickup_date",
                "Predicted Value LOCAL ONLY": "Fake Private Pickup Date",
                "Status": "needs_review",
                "Needs Review": "yes",
            }
        ],
    )
    _write_csv(
        root / REVIEW_RATE_REVIEW_CSV,
        RATE_REVIEW_COLUMNS,
        [{"Measurement Alias": "RATECON_001", "Rate Field Type": "rate"}],
    )


class AnalyzeLocalRateConReviewOutputsCliTests(unittest.TestCase):
    def test_cli_generates_reports_and_safe_console(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_review_outputs(root)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = cli.main(
                    [
                        "--input-dir",
                        tmp,
                        "--write-md",
                        "--write-json",
                        "--include-local-document-names-local-only",
                    ]
                )
            output = stdout.getvalue()

            md = root / "local_review_analysis.md"
            json_path = root / "local_review_analysis.json"

            self.assertEqual(exit_code, 0)
            self.assertTrue(md.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("documents_analyzed: 1", output)
            self.assertIn("recommended_next_fix", output)
            self.assertIn("local_review_analysis.md", output)
            self.assertNotIn("Fake Private", output)
            self.assertNotIn(tmp, output)


if __name__ == "__main__":
    unittest.main()
