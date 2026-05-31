import json
import unittest

from app.document_ai.load_identifier_source_line_audit import (
    LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER,
    LOAD_ID_LABEL_CATEGORY_PO_NUMBER,
    LOAD_ID_SOURCE_LINE_ANALYSIS_VERSION,
    LOAD_ID_SOURCE_REASON_LABEL_CLASSIFIED_NON_PRIMARY,
    LOAD_ID_SOURCE_REASON_LABEL_DETECTED_UNCLASSIFIED,
    LOAD_ID_SOURCE_REASON_NO_SHARED_ROOT_CAUSE,
    LOAD_ID_SOURCE_REASON_ONLY_NON_PRIMARY_REFS_VISIBLE,
    LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_CORE_MAPPED,
    LOAD_ID_SOURCE_REASON_SOURCE_LINE_ABSENT,
    LOAD_ID_SOURCE_SECTION_HEADER,
    LOAD_ID_SOURCE_STAGE_CORE_MAPPED,
    LOAD_ID_SOURCE_STAGE_LABEL_CLASSIFIED,
    LOAD_ID_SOURCE_STAGE_SOURCE_LINE,
    build_load_id_source_line_aggregate,
    build_load_id_source_line_record,
    build_load_id_source_line_result,
)


class LoadIdentifierSourceLineAuditTests(unittest.TestCase):
    def test_source_line_absent_record_blocks_fix(self):
        record = build_load_id_source_line_record(
            measurement_alias="RATECON_001",
            stage=LOAD_ID_SOURCE_STAGE_SOURCE_LINE,
            reason=LOAD_ID_SOURCE_REASON_SOURCE_LINE_ABSENT,
        )

        self.assertEqual(record["reason"], "source_line_absent")
        self.assertEqual(record["recommended_fix_bucket"], "local_human_review")

    def test_label_present_but_unclassified_is_fixable(self):
        record = build_load_id_source_line_record(
            measurement_alias="RATECON_002",
            stage=LOAD_ID_SOURCE_STAGE_LABEL_CLASSIFIED,
            reason=LOAD_ID_SOURCE_REASON_LABEL_DETECTED_UNCLASSIFIED,
            source_section_category=LOAD_ID_SOURCE_SECTION_HEADER,
            identifier_like_line_count=1,
            detected_label_count=1,
        )

        self.assertEqual(record["source_section_category"], "header")
        self.assertEqual(
            record["recommended_fix_bucket"],
            "label_classification",
        )

    def test_label_classified_non_primary_stays_review_only(self):
        record = build_load_id_source_line_record(
            measurement_alias="RATECON_003",
            reason=LOAD_ID_SOURCE_REASON_LABEL_CLASSIFIED_NON_PRIMARY,
            label_category=LOAD_ID_LABEL_CATEGORY_PO_NUMBER,
            rejected_non_primary_count=1,
        )

        self.assertEqual(record["label_category"], "po_number")
        self.assertEqual(record["recommended_fix_bucket"], "local_human_review")

    def test_primary_not_core_mapped_can_allow_fix_when_shared(self):
        records = [
            build_load_id_source_line_record(
                measurement_alias=f"RATECON_00{index}",
                stage=LOAD_ID_SOURCE_STAGE_CORE_MAPPED,
                reason=LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_CORE_MAPPED,
                label_category=LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER,
                primary_candidate_count=1,
            )
            for index in range(1, 4)
        ]

        aggregate = build_load_id_source_line_aggregate(records, document_count=3)

        self.assertTrue(aggregate["fix_allowed"])
        self.assertEqual(
            aggregate["selected_root_cause"],
            LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_CORE_MAPPED,
        )
        self.assertEqual(aggregate["recommended_next_action"], "core_mapping")

    def test_no_shared_root_cause_keeps_fix_disallowed(self):
        aggregate = build_load_id_source_line_aggregate(
            [
                build_load_id_source_line_record(
                    measurement_alias="RATECON_001",
                    reason=LOAD_ID_SOURCE_REASON_SOURCE_LINE_ABSENT,
                ),
                build_load_id_source_line_record(
                    measurement_alias="RATECON_002",
                    reason=LOAD_ID_SOURCE_REASON_ONLY_NON_PRIMARY_REFS_VISIBLE,
                ),
                build_load_id_source_line_record(
                    measurement_alias="RATECON_003",
                    reason=LOAD_ID_SOURCE_REASON_NO_SHARED_ROOT_CAUSE,
                ),
            ],
            document_count=3,
        )

        self.assertFalse(aggregate["fix_allowed"])
        self.assertEqual(aggregate["recommended_next_action"], "local_human_review")

    def test_serialization_contains_no_private_values_or_line_text(self):
        result = build_load_id_source_line_result(
            [
                build_load_id_source_line_record(
                    measurement_alias="RATECON_001",
                    label_category=LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER,
                    primary_candidate_count=1,
                )
            ],
            document_count=1,
        )

        payload = json.loads(json.dumps(result))
        self.assertEqual(
            payload["analysis_version"],
            LOAD_ID_SOURCE_LINE_ANALYSIS_VERSION,
        )
        self.assertFalse(payload["private_values_included"])
        self.assertFalse(payload["raw_text_included"])
        self.assertFalse(payload["line_text_included"])
        self.assertNotIn("FAKE-LOAD", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
