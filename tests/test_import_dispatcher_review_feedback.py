import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.document_ai.dispatcher_review_table import (
    DISPATCHER_REVIEW_V3_AUDIT_CSV,
    DISPATCHER_REVIEW_V3_REVIEW_CSV,
)
from scripts import import_dispatcher_review_feedback as cli


def _write_csv(path, rows):
    columns = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_audit(root):
    _write_csv(
        root / DISPATCHER_REVIEW_V3_AUDIT_CSV,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "final_rate",
                "Predicted Value LOCAL ONLY": "FAKE_RATE_OLD",
                "Dispatcher Value At Export LOCAL ONLY": "FAKE_RATE_OLD",
            },
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "load_number",
                "Predicted Value LOCAL ONLY": "",
                "Dispatcher Value At Export LOCAL ONLY": "",
            },
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "pickup",
                "Predicted Value LOCAL ONLY": "FAKE_PICKUP_OLD",
                "Dispatcher Value At Export LOCAL ONLY": "FAKE_PICKUP_OLD",
            },
        ],
    )


class ImportDispatcherReviewFeedbackTests(unittest.TestCase):
    def test_detects_correction_columns_without_printing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_audit(root)
            _write_csv(
                root / cli.DISPATCHER_COMPLETED_REVIEW_CSV,
                [
                    {
                        "Measurement Alias": "RATECON_001",
                        "Final Rate": "FAKE_RATE_OLD",
                        "Load No": "",
                        "Pickup": "FAKE_PICKUP_OLD",
                        "User Corrected Final Rate": "FAKE_RATE_NEW",
                        "User Corrected Load No": "FAKE_LOAD_NEW",
                        "User Notes Local Only": "FAKE_PRIVATE_NOTE",
                    }
                ],
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", str(root), "--output-dir", str(root)])

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertIn("changed_field_count: 2", output)
            self.assertIn("wrong_rate", output)
            self.assertIn("load_id_missing", output)
            self.assertNotIn("FAKE_RATE_NEW", output)
            self.assertNotIn("FAKE_PRIVATE_NOTE", output)

            payload = json.loads(
                (root / cli.DISPATCHER_FEEDBACK_SUMMARY_JSON).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["aggregate"]["changed_field_count"], 2)
            self.assertNotIn("FAKE_RATE_NEW", json.dumps(payload))

    def test_detects_direct_edited_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_audit(root)
            _write_csv(
                root / cli.DISPATCHER_COMPLETED_REVIEW_CSV,
                [
                    {
                        "Measurement Alias": "RATECON_001",
                        "Pickup": "FAKE_PICKUP_NEW",
                    }
                ],
            )

            aggregate, _written = cli.import_dispatcher_feedback(root, root)

            self.assertEqual(aggregate["changed_field_count"], 1)
            self.assertEqual(aggregate["issue_type_counts"], {"wrong_pickup": 1})

    def test_missing_completed_feedback_is_friendly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_audit(root)
            _write_csv(
                root / DISPATCHER_REVIEW_V3_REVIEW_CSV,
                [{"Measurement Alias": "RATECON_001", "Pickup": "FAKE_PICKUP_OLD"}],
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", str(root), "--output-dir", str(root)])

            self.assertEqual(result, 0)
            self.assertIn("no_completed_dispatcher_feedback_found", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
