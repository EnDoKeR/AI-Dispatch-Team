import csv
import tempfile
import unittest
from pathlib import Path

from app.document_ai.review_feedback_import import (
    REVIEW_FEEDBACK_SUMMARY_VERSION,
    import_review_feedback_csv,
    summarize_review_feedback_rows,
)


def _row(alias, field_name, answer, issue_type=""):
    return {
        "Measurement Alias": alias,
        "Field Name": field_name,
        "Predicted Value LOCAL ONLY": "Fake Value",
        "User Correct? yes/no/unknown": answer,
        "User Expected Value LOCAL ONLY": "Fake Expected",
        "User Issue Type": issue_type,
        "User Notes Local Only": "Fake local note",
    }


class ReviewFeedbackImportTests(unittest.TestCase):
    def test_summarizes_fake_completed_rows_without_values(self):
        summary = summarize_review_feedback_rows(
            [
                _row("RATECON_001", "pickup_date", "yes"),
                _row("RATECON_001", "delivery_date", "no", "wrong_date"),
                _row("RATECON_002", "rate", "unknown"),
            ]
        )

        self.assertEqual(summary["rows_loaded"], 3)
        self.assertEqual(summary["reviewed_field_count"], 3)
        self.assertEqual(summary["correct_count"], 1)
        self.assertEqual(summary["incorrect_count"], 1)
        self.assertEqual(summary["unknown_count"], 1)
        self.assertEqual(summary["issue_type_counts"], {"wrong_date": 1})
        self.assertTrue(summary["safe_summary_only"])
        self.assertEqual(summary["summary_version"], REVIEW_FEEDBACK_SUMMARY_VERSION)
        self.assertNotIn("Fake Value", str(summary))
        self.assertNotIn("Fake Expected", str(summary))

    def test_flags_high_error_fields_and_aliases(self):
        summary = summarize_review_feedback_rows(
            [
                _row("RATECON_001", "pickup_date", "no", "wrong_date"),
                _row("RATECON_001", "pickup_date", "yes"),
                _row("RATECON_002", "rate", "yes"),
            ]
        )

        self.assertIn("pickup_date", summary["fields_with_high_error_rate"])
        self.assertIn("RATECON_001", summary["aliases_with_high_error_rate"])
        self.assertNotIn("rate", summary["fields_with_high_error_rate"])

    def test_imports_fake_completed_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "completed_review.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(_row("", "", "").keys()))
                writer.writeheader()
                writer.writerow(_row("RATECON_003", "equipment", "no", "wrong_equipment"))

            summary = import_review_feedback_csv(path)

        self.assertEqual(summary["rows_loaded"], 1)
        self.assertEqual(summary["incorrect_count"], 1)
        self.assertEqual(summary["issue_type_counts"], {"wrong_equipment": 1})

    def test_malformed_csv_returns_safe_warning(self):
        summary = summarize_review_feedback_rows([{"Measurement Alias": "RATECON_001"}])

        self.assertEqual(summary["rows_loaded"], 0)
        self.assertIn("malformed_review_feedback_csv", summary["warning_codes"])
        self.assertTrue(summary["safe_summary_only"])


if __name__ == "__main__":
    unittest.main()
