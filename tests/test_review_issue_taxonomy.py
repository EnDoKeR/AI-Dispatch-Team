import json
import unittest

from app.document_ai.review_issue_taxonomy import (
    REVIEW_ISSUE_TYPE_OCR_NEEDED,
    build_review_feedback_aggregate,
    build_review_feedback_row,
    review_feedback_row_from_csv,
)


class ReviewIssueTaxonomyTests(unittest.TestCase):
    def test_counts_issue_types_and_recommends_target(self):
        rows = [
            build_review_feedback_row(
                measurement_alias="RATECON_001",
                row_type="rate",
                field_name="rate",
                review_decision="no",
                issue_type="wrong_rate",
            ),
            build_review_feedback_row(
                measurement_alias="RATECON_002",
                row_type="rate",
                field_name="rate",
                review_decision="no",
                issue_type="accessorial_confused_as_rate",
            ),
            build_review_feedback_row(
                measurement_alias="RATECON_003",
                row_type="field",
                field_name="broker_name",
                review_decision="yes",
            ),
        ]

        aggregate = build_review_feedback_aggregate(rows)

        self.assertEqual(aggregate["rows_loaded"], 3)
        self.assertEqual(aggregate["reviewed_count"], 3)
        self.assertEqual(aggregate["correct_count"], 1)
        self.assertEqual(aggregate["incorrect_count"], 2)
        self.assertEqual(
            aggregate["issue_type_counts"],
            {"accessorial_confused_as_rate": 1, "wrong_rate": 1},
        )
        self.assertEqual(
            aggregate["recommended_next_repair_target"],
            "rate_resolution",
        )

    def test_expected_value_and_private_note_are_booleans_only(self):
        row = review_feedback_row_from_csv(
            {
                "Measurement Alias": "RATECON_004",
                "Field Name": "pickup_date",
                "Status": "missing",
                "User Correct? yes/no/unknown": "no",
                "User Issue Type": "wrong_date",
                "User Expected Value LOCAL ONLY": "FAKE_EXPECTED_PRIVATE",
                "User Notes Local Only": "FAKE_PRIVATE_NOTE",
            },
            sheet_name="Core_Field_Review",
            row_type="field",
        )

        self.assertTrue(row["user_expected_value_present"])
        self.assertTrue(row["private_note_present"])
        encoded = json.dumps(row, sort_keys=True)
        self.assertNotIn("FAKE_EXPECTED_PRIVATE", encoded)
        self.assertNotIn("FAKE_PRIVATE_NOTE", encoded)

    def test_normalizes_ocr_issue_alias(self):
        row = build_review_feedback_row(
            measurement_alias="RATECON_005",
            row_type="document",
            review_decision="no",
            issue_type="ocr_needed",
        )

        aggregate = build_review_feedback_aggregate([row])

        self.assertEqual(
            aggregate["issue_type_counts"],
            {REVIEW_ISSUE_TYPE_OCR_NEEDED: 1},
        )
        self.assertEqual(aggregate["recommended_next_repair_target"], "OCR_design")

    def test_serialization_flags_are_safe(self):
        aggregate = build_review_feedback_aggregate(
            [
                build_review_feedback_row(
                    measurement_alias="RATECON_006",
                    field_name="load_number",
                    review_decision="no",
                    issue_type="load_id_missing",
                )
            ]
        )

        self.assertFalse(aggregate["private_values_included"])
        self.assertFalse(aggregate["raw_text_included"])
        self.assertFalse(aggregate["money_values_included"])
        json.dumps(aggregate)


if __name__ == "__main__":
    unittest.main()
