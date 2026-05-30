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

    def test_measurement_row_supports_safe_template_summary_fields(self):
        row = build_private_ratecon_measurement_row(
            document_alias="RATECON_001",
            template_status="matched",
            selected_template_id="PRIVATE_TEMPLATE_001",
            template_source="private_local",
            template_confidence_bucket="high",
        )

        payload = json.dumps(row)

        self.assertEqual(row["selected_template_id"], "PRIVATE_TEMPLATE_001")
        self.assertEqual(row["template_source"], "private_local")
        self.assertEqual(row["template_confidence_bucket"], "high")
        self.assertNotIn("PRIVATE REAL BROKER", payload)

    def test_measurement_row_supports_classification_summary_fields(self):
        row = build_private_ratecon_measurement_row(
            document_alias="RATECON_001",
            document_type="BILL_OF_LADING",
            ratecon_eligible=False,
            supplemental_only=True,
            page_role_counts={"BOL": 1},
            section_role_counts={"BOL_BODY": 1},
            classification_status="supplemental_only",
            classification_warning_codes=["supplemental_page_skipped_for_core_ratecon"],
        )

        payload = json.dumps(row)

        self.assertEqual(row["document_type"], "BILL_OF_LADING")
        self.assertFalse(row["ratecon_eligible"])
        self.assertTrue(row["supplemental_only"])
        self.assertEqual(row["page_role_counts"], {"BOL": 1})
        self.assertEqual(row["section_role_counts"], {"BOL_BODY": 1})
        self.assertNotIn("raw_text", row)
        self.assertNotIn("FAKE BROKER LLC", payload)

    def test_aggregate_serializes(self):
        aggregate = build_private_ratecon_measurement_aggregate(
            document_count=2,
            triage_route_counts={"DIGITAL_TEXT": 1, "OCR_NEEDED": 1},
            extraction_status_counts={"TEXT_EXTRACTED": 1, "EMPTY_TEXT": 1},
            critical_field_missing_counts={"rate": 1},
            document_type_counts={"RATE_CONFIRMATION": 1, "BILL_OF_LADING": 1},
            ratecon_eligible_count=1,
            supplemental_only_count=1,
            page_role_counts={"MAIN_RATECONF": 1, "BOL": 1},
            section_role_counts={"RATE_SUMMARY": 1, "BOL_BODY": 1},
            eligible_critical_field_missing_counts={"rate": 1},
            eligible_critical_field_denominator=1,
        )

        json.dumps(aggregate)
        self.assertFalse(aggregate["raw_text_saved"])
        self.assertTrue(aggregate["private_values_redacted"])
        self.assertEqual(aggregate["ratecon_eligible_count"], 1)
        self.assertEqual(aggregate["supplemental_only_count"], 1)

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
