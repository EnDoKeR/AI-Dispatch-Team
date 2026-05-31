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
            extraction_relevant=False,
            normal_load_movement=False,
            supplemental_only=True,
            page_role_counts={"BOL": 1},
            section_role_counts={"BOL_BODY": 1},
            extraction_scope_counts={"NON_RATECON_SKIP": 1},
            classification_status="supplemental_only",
            classification_warning_codes=["supplemental_page_skipped_for_core_ratecon"],
            skipped_by_scope=True,
        )

        payload = json.dumps(row)

        self.assertEqual(row["document_type"], "BILL_OF_LADING")
        self.assertFalse(row["ratecon_eligible"])
        self.assertFalse(row["extraction_relevant"])
        self.assertFalse(row["normal_load_movement"])
        self.assertTrue(row["supplemental_only"])
        self.assertEqual(row["page_role_counts"], {"BOL": 1})
        self.assertEqual(row["section_role_counts"], {"BOL_BODY": 1})
        self.assertEqual(row["extraction_scope_counts"], {"NON_RATECON_SKIP": 1})
        self.assertTrue(row["skipped_by_scope"])
        self.assertNotIn("raw_text", row)
        self.assertNotIn("FAKE BROKER LLC", payload)

    def test_measurement_row_supports_safe_stop_span_coverage_metrics(self):
        row = build_private_ratecon_measurement_row(
            document_alias="RATECON_001",
            stop_span_coverage_metrics={
                "span_field_candidate_count_by_field": {"date": 1},
                "core_field_mapping_count_by_field": {"pickup_date": 1},
                "private_values_included": False,
                "raw_text_included": False,
            },
        )

        payload = json.dumps(row)

        self.assertEqual(
            row["stop_span_coverage_metrics"]["span_field_candidate_count_by_field"],
            {"date": 1},
        )
        self.assertFalse(row["stop_span_coverage_metrics"]["private_values_included"])
        self.assertFalse(row["stop_span_coverage_metrics"]["raw_text_included"])
        self.assertNotIn("Fake Broker", payload)

    def test_measurement_row_supports_safe_load_identifier_coverage_metrics(self):
        row = build_private_ratecon_measurement_row(
            document_alias="RATECON_001",
            load_identifier_coverage_metrics={
                "identifier_label_feature_count": 2,
                "primary_identifier_candidate_count": 1,
                "typed_reference_candidate_count": 1,
                "core_load_number_mapping_count": 1,
                "rejected_reference_as_load_id_count": 1,
                "private_values_included": False,
                "raw_text_included": False,
            },
        )

        payload = json.dumps(row)

        self.assertEqual(
            row["load_identifier_coverage_metrics"]["primary_identifier_candidate_count"],
            1,
        )
        self.assertFalse(row["load_identifier_coverage_metrics"]["private_values_included"])
        self.assertFalse(row["load_identifier_coverage_metrics"]["raw_text_included"])
        self.assertNotIn("FAKE-LOAD", payload)

    def test_measurement_row_supports_safe_load_identifier_audit_records(self):
        row = build_private_ratecon_measurement_row(
            document_alias="RATECON_001",
            load_identifier_audit_records=[
                {
                    "measurement_alias": "RATECON_001",
                    "stage": "non_primary_reference_rejected",
                    "status": "rejected",
                    "reason": "only_non_primary_references_found",
                    "identifier_label_category": "po_number",
                    "private_values_included": False,
                    "raw_text_included": False,
                }
            ],
        )

        payload = json.dumps(row)

        self.assertEqual(len(row["load_identifier_audit_records"]), 1)
        self.assertEqual(
            row["load_identifier_audit_records"][0]["identifier_label_category"],
            "po_number",
        )
        self.assertNotIn("FAKE-PO", payload)

    def test_aggregate_serializes(self):
        aggregate = build_private_ratecon_measurement_aggregate(
            document_count=2,
            triage_route_counts={"DIGITAL_TEXT": 1, "OCR_NEEDED": 1},
            extraction_status_counts={"TEXT_EXTRACTED": 1, "EMPTY_TEXT": 1},
            critical_field_missing_counts={"rate": 1},
            document_type_counts={"RATE_CONFIRMATION": 1, "BILL_OF_LADING": 1},
            ratecon_eligible_count=1,
            extraction_relevant_count=1,
            normal_load_movement_count=1,
            ocr_needed_count=1,
            classification_status_counts={"ratecon_eligible": 1, "supplemental_only": 1},
            supplemental_only_count=1,
            page_role_counts={"MAIN_RATECONF": 1, "BOL": 1},
            section_role_counts={"RATE_SUMMARY": 1, "BOL_BODY": 1},
            extraction_scope_counts={"RATECON_CORE_ALLOWED": 1, "NON_RATECON_SKIP": 1},
            eligible_critical_field_missing_counts={"rate": 1},
            eligible_critical_field_denominator=1,
            normal_load_critical_field_missing_counts={"rate": 1},
            normal_load_critical_field_denominator=1,
        )

        json.dumps(aggregate)
        self.assertFalse(aggregate["raw_text_saved"])
        self.assertTrue(aggregate["private_values_redacted"])
        self.assertEqual(aggregate["ratecon_eligible_count"], 1)
        self.assertEqual(aggregate["extraction_relevant_count"], 1)
        self.assertEqual(aggregate["normal_load_movement_count"], 1)
        self.assertEqual(aggregate["ocr_needed_count"], 1)
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
