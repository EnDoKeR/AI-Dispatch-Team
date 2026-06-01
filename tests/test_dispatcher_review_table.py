import json
import unittest

from app.document_ai.dispatcher_review_table import (
    aggregate_dispatcher_feedback,
    build_dispatcher_audit_row,
    build_dispatcher_feedback_row,
    build_dispatcher_review_row,
    infer_dispatcher_issue_type,
)


class DispatcherReviewTableTests(unittest.TestCase):
    def test_creates_dispatcher_review_row(self):
        row = build_dispatcher_review_row(
            folder_order=1,
            measurement_alias="RATECON_001",
            broker="Fake Broker",
            pickup="Fake Pickup",
            final_rate="Fake Rate",
            top_blockers="rate;load_number",
        )

        self.assertEqual(row["Measurement Alias"], "RATECON_001")
        self.assertEqual(row["Broker"], "Fake Broker")
        self.assertEqual(row["Pickup"], "Fake Pickup")
        self.assertEqual(row["Top Blockers"], "rate;load_number")
        self.assertIn("User Corrected Broker", row)

    def test_creates_audit_row(self):
        row = build_dispatcher_audit_row(
            measurement_alias="RATECON_002",
            field_name="Load No",
            predicted_status="missing",
            candidate_count=0,
            gap_reason="no_candidate",
            source_sheet="Core_Field_Review",
        )

        self.assertEqual(row["Field Name"], "load_no")
        self.assertEqual(row["Predicted Status"], "missing")
        self.assertEqual(row["Gap Reason"], "no_candidate")

    def test_infers_changed_value_issue_type(self):
        self.assertEqual(
            infer_dispatcher_issue_type("final_rate", "Fake Old", "Fake New"),
            "wrong_rate",
        )
        self.assertEqual(
            infer_dispatcher_issue_type("load_number", "", "Fake Load"),
            "load_id_missing",
        )
        self.assertEqual(
            infer_dispatcher_issue_type("broker", "", "Fake Broker"),
            "broker_missing",
        )

    def test_feedback_aggregate_counts_without_values(self):
        rows = [
            build_dispatcher_feedback_row(
                measurement_alias="RATECON_001",
                field_name="final_rate",
                original_predicted_value="Fake Old Rate",
                user_corrected_value="Fake New Rate",
            ),
            build_dispatcher_feedback_row(
                measurement_alias="RATECON_002",
                field_name="pickup",
                original_predicted_value="Fake Pickup",
                user_corrected_value="Fake Pickup",
            ),
        ]

        aggregate = aggregate_dispatcher_feedback(rows)

        self.assertEqual(aggregate["rows_loaded"], 2)
        self.assertEqual(aggregate["documents_reviewed"], 2)
        self.assertEqual(aggregate["changed_field_count"], 1)
        self.assertEqual(aggregate["issue_type_counts"], {"wrong_rate": 1})
        self.assertEqual(
            aggregate["recommended_next_repair_target"],
            "rate_resolution",
        )
        encoded = json.dumps(aggregate)
        self.assertNotIn("Fake Old Rate", encoded)
        self.assertNotIn("Fake New Rate", encoded)
        self.assertFalse(aggregate["private_values_included"])


if __name__ == "__main__":
    unittest.main()
