import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts import import_ratecon_review_feedback as cli


def _write_csv(path, rows):
    columns = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


class ImportRateConReviewFeedbackCliTests(unittest.TestCase):
    def test_missing_completed_feedback_is_friendly(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", tmp, "--output-dir", tmp])

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertIn("no_completed_feedback_found", output)
            self.assertIn("recommended_next_repair_target: human_review_continue", output)
            self.assertTrue((Path(tmp) / cli.REVIEW_FEEDBACK_SUMMARY_JSON).exists())

    def test_imports_completed_feedback_without_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(
                root / "ratecon_review_v2_rates_completed.csv",
                [
                    {
                        "Measurement Alias": "RATECON_001",
                        "Rate Candidate Type": "rate",
                        "Predicted Value LOCAL ONLY": "FAKE_RATE_PRIVATE",
                        "User Correct? yes/no/unknown": "no",
                        "User Expected Value LOCAL ONLY": "FAKE_EXPECTED_PRIVATE",
                        "User Issue Type": "wrong_rate",
                        "User Notes Local Only": "FAKE_NOTE_PRIVATE",
                    },
                    {
                        "Measurement Alias": "RATECON_002",
                        "Rate Candidate Type": "rate",
                        "Predicted Value LOCAL ONLY": "FAKE_RATE_PRIVATE_2",
                        "User Correct? yes/no/unknown": "yes",
                        "User Issue Type": "",
                    },
                ],
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", str(root), "--output-dir", str(root)])

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertIn("rows_loaded: 2", output)
            self.assertIn("incorrect_count: 1", output)
            self.assertIn("wrong_rate", output)
            self.assertNotIn("FAKE_RATE_PRIVATE", output)
            self.assertNotIn("FAKE_EXPECTED_PRIVATE", output)
            self.assertNotIn("FAKE_NOTE_PRIVATE", output)

            payload = json.loads(
                (root / cli.REVIEW_FEEDBACK_SUMMARY_JSON).read_text(encoding="utf-8")
            )
            self.assertEqual(
                payload["aggregate"]["recommended_next_repair_target"],
                "rate_resolution",
            )
            self.assertNotIn("FAKE_EXPECTED_PRIVATE", json.dumps(payload))

    def test_imports_edited_in_place_only_when_feedback_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(
                root / "ratecon_review_v2_core_fields.csv",
                [
                    {
                        "Measurement Alias": "RATECON_003",
                        "Field Name": "load_number",
                        "User Correct? yes/no/unknown": "no",
                        "User Issue Type": "load_id_missing",
                    }
                ],
            )

            aggregate, used_files, _written = cli.import_feedback(root, root)

            self.assertEqual(aggregate["rows_loaded"], 1)
            self.assertEqual(used_files, ["ratecon_review_v2_core_fields.csv"])
            self.assertEqual(
                aggregate["recommended_next_repair_target"],
                "load_identifier_extraction",
            )


if __name__ == "__main__":
    unittest.main()
