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
    analyze_load_id_source_lines_from_rows,
    build_load_identifier_source_line_metrics,
    build_load_id_source_line_aggregate,
    build_load_id_source_line_record,
    build_load_id_source_line_result,
    scan_load_identifier_source_lines,
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

    def test_fake_header_identifier_line_counts_as_header_source(self):
        artifact = {
            "pages": [
                {
                    "text": "Rate Confirmation\nLoad Number: FAKE-LOAD-001\nCarrier Name: FAKE CARRIER"
                }
            ]
        }

        scan = scan_load_identifier_source_lines(artifact)

        self.assertEqual(scan["identifier_like_line_count"], 1)
        self.assertEqual(scan["section_counts"]["load_identity"], 1)
        self.assertEqual(scan["label_category_counts"]["load_number"], 1)
        self.assertFalse(scan["line_text_included"])
        self.assertNotIn("FAKE-LOAD-001", json.dumps(scan))

    def test_stop_reference_counts_as_non_primary_stop_section(self):
        artifact = {
            "pages": [
                {
                    "text": "Pickup Stop\nReference #: FAKE-REF-001\nDelivery Stop"
                }
            ]
        }

        scan = scan_load_identifier_source_lines(artifact)

        self.assertEqual(scan["identifier_like_line_count"], 1)
        self.assertEqual(scan["section_counts"]["stop_section"], 1)
        self.assertEqual(scan["label_category_counts"]["generic_reference"], 1)

    def test_metrics_track_primary_and_core_mapping_counts(self):
        artifact = {"pages": [{"text": "Load Number: FAKE-LOAD-001"}]}
        candidate = {
            "field_name": "load_number",
            "identifier_type": "broker_load_number",
            "value_type": "broker_load_number",
            "primary_load_identifier_candidate": True,
        }
        resolution = {
            "resolutions": [
                {"field_name": "load_number", "status": "resolved"},
            ]
        }

        metrics = build_load_identifier_source_line_metrics(
            full_artifact=artifact,
            scoped_artifact=artifact,
            candidates=[candidate],
            resolution_result=resolution,
        )

        self.assertEqual(metrics["identifier_like_source_line_count"], 1)
        self.assertEqual(metrics["primary_candidate_count"], 1)
        self.assertEqual(metrics["core_mapping_count"], 1)
        self.assertFalse(metrics["line_text_included"])

    def test_analyzer_marks_ocr_rows_as_not_code_fixable(self):
        result = analyze_load_id_source_lines_from_rows(
            [
                {
                    "document_alias": "RATECON_001",
                    "triage_route": "OCR_NEEDED",
                    "extraction_status": "EMPTY_TEXT",
                    "char_count": 0,
                }
            ]
        )

        aggregate = result["aggregate"]
        self.assertFalse(aggregate["fix_allowed"])
        self.assertEqual(
            aggregate["records_by_reason"]["ocr_needed_or_weak_text"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
