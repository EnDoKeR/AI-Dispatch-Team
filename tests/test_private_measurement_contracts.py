import json
import unittest

from app.document_ai.private_measurement import (
    BLOCKER_OCR_NEEDED,
    CONFIDENCE_BUCKET_HIGH,
    FIELD_STATUS_RESOLVED,
    build_field_status_summary,
    build_private_document_alias,
    build_private_ratecon_measurement_aggregate,
    build_private_ratecon_measurement_row,
    build_safe_measurement_output_policy,
)


class PrivateMeasurementContractTests(unittest.TestCase):
    def test_document_alias_defaults_do_not_include_filename(self):
        alias = build_private_document_alias(alias="RATECON_001", original_index=1)

        self.assertEqual(alias["alias"], "RATECON_001")
        self.assertFalse(alias["filename_included"])
        self.assertEqual(alias["file_hash_prefix"], "")

    def test_field_status_summary_does_not_include_value(self):
        summary = build_field_status_summary(
            field_name="rate",
            status=FIELD_STATUS_RESOLVED,
            confidence_bucket=CONFIDENCE_BUCKET_HIGH,
            candidate_count=2,
            selected_candidate_present=True,
            safe_reasons=["selected_highest_confidence_candidate"],
        )

        self.assertTrue(summary["value_redacted"])
        self.assertNotIn("value", summary)
        self.assertEqual(summary["field_name"], "rate")

    def test_measurement_row_serializes_and_redacts_private_values(self):
        row = build_private_ratecon_measurement_row(
            document_alias="RATECON_001",
            page_count=2,
            char_count=1000,
            triage_route="DIGITAL_TEXT",
            extraction_status="TEXT_EXTRACTED",
            candidate_counts_by_field={"rate": 1},
            field_statuses=[
                build_field_status_summary(
                    field_name="rate",
                    status=FIELD_STATUS_RESOLVED,
                    confidence_bucket=CONFIDENCE_BUCKET_HIGH,
                )
            ],
            blocker_categories=[BLOCKER_OCR_NEEDED],
        )

        payload = json.dumps(row)

        self.assertFalse(row["raw_text_saved"])
        self.assertTrue(row["private_values_redacted"])
        self.assertNotIn("raw_text", row)
        self.assertNotIn("FAKE BROKER LLC", payload)

    def test_aggregate_serializes(self):
        aggregate = build_private_ratecon_measurement_aggregate(
            document_count=2,
            triage_route_counts={"DIGITAL_TEXT": 1, "OCR_NEEDED": 1},
            extraction_status_counts={"TEXT_EXTRACTED": 1, "EMPTY_TEXT": 1},
            critical_field_missing_counts={"rate": 1},
        )

        json.dumps(aggregate)
        self.assertFalse(aggregate["raw_text_saved"])
        self.assertTrue(aggregate["private_values_redacted"])

    def test_output_policy_defaults_are_shareable_and_safe(self):
        policy = build_safe_measurement_output_policy()

        self.assertFalse(policy["include_filenames"])
        self.assertFalse(policy["include_file_hash_prefix"])
        self.assertFalse(policy["include_private_values"])
        self.assertFalse(policy["include_raw_text"])
        self.assertTrue(policy["output_is_shareable"])

    def test_output_policy_rejects_raw_text(self):
        with self.assertRaises(ValueError):
            build_safe_measurement_output_policy(include_raw_text=True)

    def test_private_values_make_policy_non_shareable(self):
        policy = build_safe_measurement_output_policy(include_private_values=True)

        self.assertTrue(policy["include_private_values"])
        self.assertFalse(policy["output_is_shareable"])

    def test_private_values_cannot_be_requested_for_shareable_output(self):
        with self.assertRaises(ValueError):
            build_safe_measurement_output_policy(
                include_private_values=True,
                output_is_shareable=True,
            )


if __name__ == "__main__":
    unittest.main()
