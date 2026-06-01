import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.document_ai.dispatcher_review_table import (
    DISPATCHER_REVIEW_V3_AUDIT_CSV,
    DISPATCHER_REVIEW_V3_REVIEW_CSV,
)
from app.document_ai.ratecon_review_workbook import (
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_V2_CORE_FIELDS_CSV,
    REVIEW_V2_DOCUMENT_SUMMARY_CSV,
    REVIEW_V2_LOAD_IDS_CSV,
    REVIEW_V2_RATES_CSV,
    REVIEW_V2_STOPS_CSV,
)
from scripts import generate_dispatcher_review_table_v3 as cli


def _write_csv(path, rows):
    columns = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_fake_inputs(root):
    _write_csv(
        root / REVIEW_V2_DOCUMENT_SUMMARY_CSV,
        [
            {
                "Folder Order": "1",
                "Measurement Alias": "RATECON_001",
                "Document Type": "LOAD_CONFIRMATION",
                "OCR Needed": "no",
                "Extraction Relevant": "yes",
                "Readiness Level": "not_ready",
                "Review Priority": "high",
                "Top Blockers": "rate;load_number",
            }
        ],
    )
    _write_csv(
        root / REVIEW_V2_CORE_FIELDS_CSV,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "broker_name",
                "Predicted Value LOCAL ONLY": "FAKE_BROKER_PRIVATE",
                "Predicted Status": "resolved",
            },
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "rate",
                "Predicted Value LOCAL ONLY": "FAKE_RATE_PRIVATE",
                "Predicted Status": "conflict",
            },
        ],
    )
    _write_csv(
        root / REVIEW_V2_STOPS_CSV,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Stop Type": "pickup",
                "Field Name": "location",
                "Predicted Value LOCAL ONLY": "FAKE_PICKUP_PRIVATE",
                "Status": "resolved",
            }
        ],
    )
    _write_csv(root / REVIEW_V2_RATES_CSV, [{"Measurement Alias": "RATECON_001"}])
    _write_csv(root / REVIEW_V2_LOAD_IDS_CSV, [{"Measurement Alias": "RATECON_001"}])
    _write_csv(
        root / REVIEW_FIELD_REVIEW_CSV,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "commodity",
                "Predicted Value LOCAL ONLY": "FAKE_COMMODITY_PRIVATE",
                "Status": "resolved",
            }
        ],
    )


class GenerateDispatcherReviewTableV3Tests(unittest.TestCase):
    def test_cli_generates_outputs_without_printing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_inputs(root)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                result = cli.main(
                    [
                        "--input-dir",
                        str(root),
                        "--output-dir",
                        str(root),
                        "--include-private-values-local-only",
                    ]
                )

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertIn("document_rows: 1", output)
            self.assertIn("audit_rows: 12", output)
            self.assertIn("private_values_printed: False", output)
            self.assertNotIn("FAKE_BROKER_PRIVATE", output)
            self.assertTrue((root / DISPATCHER_REVIEW_V3_REVIEW_CSV).exists())
            self.assertTrue((root / DISPATCHER_REVIEW_V3_AUDIT_CSV).exists())

            with (root / DISPATCHER_REVIEW_V3_REVIEW_CSV).open(
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["Broker"], "FAKE_BROKER_PRIVATE")
            self.assertEqual(rows[0]["Final Rate"], "")

    def test_status_only_mode_blanks_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_inputs(root)

            cli.main(["--input-dir", str(root), "--output-dir", str(root)])

            with (root / DISPATCHER_REVIEW_V3_REVIEW_CSV).open(
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["Broker"], "")

    def test_missing_inputs_returns_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", tmp, "--output-dir", tmp])

            self.assertEqual(result, 2)
            self.assertIn("dispatcher_review_table_v3_error", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
