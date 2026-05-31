import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.document_ai.ratecon_review_workbook import (
    REVIEW_DOCUMENT_SUMMARY_CSV,
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_RATE_REVIEW_CSV,
    REVIEW_STOP_REVIEW_CSV,
    REVIEW_V2_CORE_FIELDS_CSV,
    REVIEW_V2_DOCUMENT_SUMMARY_CSV,
    REVIEW_V2_LOAD_IDS_CSV,
    REVIEW_V2_RATES_CSV,
    REVIEW_V2_STOPS_CSV,
)
from scripts import generate_ratecon_review_packet_v2 as cli


def _write_csv(path, rows):
    columns = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_fake_review_outputs(root):
    _write_csv(
        root / REVIEW_DOCUMENT_SUMMARY_CSV,
        [
            {
                "Folder Order": "1",
                "Local Document Name / File Stem": "fake_doc",
                "Measurement Alias": "RATECON_001",
                "Document Type": "LOAD_CONFIRMATION",
                "OCR Needed": "no",
                "Extraction Relevant": "yes",
                "Readiness Level": "not_ready",
                "Intake Core Blockers": "rate;load_number",
                "Recommended Review Priority": "high",
            }
        ],
    )
    _write_csv(
        root / REVIEW_FIELD_REVIEW_CSV,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "rate",
                "Predicted Value LOCAL ONLY": "FAKE_RATE_PRIVATE",
                "Status": "conflict",
                "Needs Review": "yes",
                "Evidence Type": "layout",
                "Policy Gap Reason": "conflict",
            },
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "load_number",
                "Predicted Value LOCAL ONLY": "FAKE_LOAD_PRIVATE",
                "Status": "missing",
                "Needs Review": "yes",
                "Policy Gap Reason": "no_candidate",
                "Load Identifier Candidate Count": "0",
                "Rejected Non-primary Reference Count": "1",
                "Load Identifier Gap Reason": "only_non_primary_reference_found",
            },
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "equipment",
                "Predicted Value LOCAL ONLY": "FAKE_EQUIPMENT_PRIVATE",
                "Status": "missing",
                "Needs Review": "yes",
            },
        ],
    )
    _write_csv(
        root / REVIEW_STOP_REVIEW_CSV,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Stop ID": "stop_1",
                "Stop Type": "pickup",
                "Stop Sequence": "1",
                "Field Name": "date",
                "Predicted Value LOCAL ONLY": "FAKE_DATE_PRIVATE",
                "Status": "missing",
                "Needs Review": "yes",
            },
            {
                "Measurement Alias": "RATECON_001",
                "Stop ID": "stop_1",
                "Stop Type": "generic",
                "Stop Sequence": "1",
                "Field Name": "notes",
                "Predicted Value LOCAL ONLY": "FAKE_NOTES_PRIVATE",
                "Status": "resolved",
                "Needs Review": "no",
            },
        ],
    )
    _write_csv(
        root / REVIEW_RATE_REVIEW_CSV,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Rate Field Type": "rate",
                "Predicted Value LOCAL ONLY": "FAKE_RATE_PRIVATE",
                "Status": "conflict",
                "Rate Conflict Reason": "multiple_different_strong_totals",
                "Main Rate Candidate Count": "2",
            }
        ],
    )


class GenerateRateConReviewPacketV2CliTests(unittest.TestCase):
    def test_cli_generates_v2_packet_without_printing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_review_outputs(root)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", str(root), "--output-dir", str(root)])

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertIn("document_rows: 1", output)
            self.assertIn("core_field_rows: 2", output)
            self.assertIn("stop_rows: 1", output)
            self.assertIn("rate_rows: 1", output)
            self.assertIn("load_id_rows: 1", output)
            self.assertIn("private_values_printed: False", output)
            self.assertNotIn("FAKE_RATE_PRIVATE", output)
            self.assertTrue((root / REVIEW_V2_DOCUMENT_SUMMARY_CSV).exists())
            self.assertTrue((root / REVIEW_V2_CORE_FIELDS_CSV).exists())
            self.assertTrue((root / REVIEW_V2_STOPS_CSV).exists())
            self.assertTrue((root / REVIEW_V2_RATES_CSV).exists())
            self.assertTrue((root / REVIEW_V2_LOAD_IDS_CSV).exists())

            with (root / REVIEW_V2_CORE_FIELDS_CSV).open(
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["Predicted Value LOCAL ONLY"], "")

    def test_cli_includes_private_values_only_with_explicit_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_review_outputs(root)

            cli.main(
                [
                    "--input-dir",
                    str(root),
                    "--output-dir",
                    str(root),
                    "--include-private-values-local-only",
                ]
            )

            with (root / REVIEW_V2_CORE_FIELDS_CSV).open(
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))
            rate_row = next(row for row in rows if row["Field Name"] == "rate")
            self.assertEqual(
                rate_row["Predicted Value LOCAL ONLY"],
                "FAKE_RATE_PRIVATE",
            )


if __name__ == "__main__":
    unittest.main()
