import json
import unittest

from app.document_ai.load_identifier_coverage_audit import (
    LOAD_ID_AUDIT_REASON_LABEL_UNCLASSIFIED,
    LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES,
    LOAD_ID_AUDIT_REASON_PRIMARY_NOT_CORE_MAPPED,
    LOAD_ID_AUDIT_STAGE_CORE_LOAD_NUMBER_MAPPED,
    LOAD_ID_AUDIT_STAGE_LABEL_CLASSIFIED,
    LOAD_ID_AUDIT_STAGE_NON_PRIMARY_REFERENCE_REJECTED,
    LOAD_ID_AUDIT_STATUS_MISSING,
    LOAD_ID_AUDIT_STATUS_REJECTED,
    LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER,
    LOAD_ID_LABEL_CATEGORY_PO_NUMBER,
    LOAD_ID_LABEL_CATEGORY_UNKNOWN,
    LOAD_IDENTIFIER_COVERAGE_ANALYSIS_VERSION,
    build_load_identifier_coverage_aggregate,
    build_load_identifier_coverage_record,
    build_load_identifier_coverage_result,
)


class LoadIdentifierCoverageAuditTests(unittest.TestCase):
    def test_only_non_primary_references_found_record(self):
        record = build_load_identifier_coverage_record(
            measurement_alias="RATECON_001",
            stage=LOAD_ID_AUDIT_STAGE_NON_PRIMARY_REFERENCE_REJECTED,
            status=LOAD_ID_AUDIT_STATUS_REJECTED,
            reason=LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES,
            identifier_label_category=LOAD_ID_LABEL_CATEGORY_PO_NUMBER,
            typed_reference_count=2,
            rejected_non_primary_count=2,
        )

        self.assertEqual(record["identifier_label_category"], "po_number")
        self.assertEqual(record["rejected_non_primary_count"], 2)
        self.assertEqual(
            record["recommended_fix_bucket"],
            "header_context_or_human_review",
        )

    def test_primary_candidate_generated_but_not_mapped_record(self):
        record = build_load_identifier_coverage_record(
            measurement_alias="RATECON_002",
            stage=LOAD_ID_AUDIT_STAGE_CORE_LOAD_NUMBER_MAPPED,
            status=LOAD_ID_AUDIT_STATUS_MISSING,
            reason=LOAD_ID_AUDIT_REASON_PRIMARY_NOT_CORE_MAPPED,
            identifier_label_category=LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER,
            candidate_count=1,
            primary_candidate_count=1,
            core_mapping_count=0,
        )

        self.assertEqual(record["primary_candidate_count"], 1)
        self.assertEqual(record["recommended_fix_bucket"], "primary_to_core_mapping")

    def test_label_not_classified_record(self):
        record = build_load_identifier_coverage_record(
            measurement_alias="RATECON_003",
            stage=LOAD_ID_AUDIT_STAGE_LABEL_CLASSIFIED,
            status=LOAD_ID_AUDIT_STATUS_MISSING,
            reason=LOAD_ID_AUDIT_REASON_LABEL_UNCLASSIFIED,
            identifier_label_category=LOAD_ID_LABEL_CATEGORY_UNKNOWN,
        )

        self.assertEqual(record["identifier_label_category"], "unknown")
        self.assertEqual(
            record["recommended_fix_bucket"],
            "load_identifier_label_classification",
        )

    def test_aggregate_counts_rejected_non_primary_categories(self):
        aggregate = build_load_identifier_coverage_aggregate(
            [
                build_load_identifier_coverage_record(
                    measurement_alias="RATECON_001",
                    reason=LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES,
                    identifier_label_category=LOAD_ID_LABEL_CATEGORY_PO_NUMBER,
                    typed_reference_count=1,
                    rejected_non_primary_count=1,
                ),
                build_load_identifier_coverage_record(
                    measurement_alias="RATECON_002",
                    reason=LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES,
                    identifier_label_category=LOAD_ID_LABEL_CATEGORY_PO_NUMBER,
                    typed_reference_count=2,
                    rejected_non_primary_count=2,
                ),
            ],
            document_count=2,
        )

        self.assertEqual(
            aggregate["records_by_reason"][
                LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES
            ],
            2,
        )
        self.assertEqual(aggregate["records_by_label_category"]["po_number"], 2)
        self.assertEqual(aggregate["typed_reference_count"], 3)
        self.assertEqual(aggregate["rejected_non_primary_count"], 3)

    def test_serialization_contains_no_private_values(self):
        result = build_load_identifier_coverage_result(
            [
                build_load_identifier_coverage_record(
                    measurement_alias="RATECON_001",
                    reason=LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES,
                    identifier_label_category=LOAD_ID_LABEL_CATEGORY_PO_NUMBER,
                    typed_reference_count=1,
                    rejected_non_primary_count=1,
                )
            ],
            document_count=1,
        )

        payload = json.loads(json.dumps(result))
        self.assertEqual(
            payload["analysis_version"],
            LOAD_IDENTIFIER_COVERAGE_ANALYSIS_VERSION,
        )
        self.assertFalse(payload["private_values_included"])
        self.assertFalse(payload["raw_text_included"])
        self.assertNotIn("FAKE-PO", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
