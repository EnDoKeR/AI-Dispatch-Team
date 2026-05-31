import json
import unittest

from app.document_ai.candidate_coverage_analysis import (
    CANDIDATE_COVERAGE_ANALYSIS_VERSION,
    COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED,
    COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED,
    COVERAGE_STAGE_CORE_FIELD_MAPPING,
    COVERAGE_STAGE_NORMALIZED_STOP_FIELD,
    COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
    COVERAGE_STATUS_MISSING,
    build_candidate_coverage_aggregate,
    build_candidate_coverage_record,
    build_candidate_coverage_result,
)


class CandidateCoverageAnalysisTests(unittest.TestCase):
    def test_builds_missing_candidate_record(self):
        record = build_candidate_coverage_record(
            measurement_alias="RATECON_001",
            field_name="pickup_date",
            stage=COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
            status=COVERAGE_STATUS_MISSING,
            gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
        )

        self.assertEqual(record["field_name"], "pickup_date")
        self.assertEqual(record["candidate_count"], 0)
        self.assertEqual(
            record["recommended_fix_bucket"],
            "stop_span_date_candidate_generation",
        )

    def test_builds_candidate_generated_but_not_normalized_record(self):
        record = build_candidate_coverage_record(
            measurement_alias="RATECON_001",
            field_name="delivery_location",
            stage=COVERAGE_STAGE_NORMALIZED_STOP_FIELD,
            status=COVERAGE_STATUS_MISSING,
            gap_reason=COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED,
            candidate_count=2,
        )

        self.assertEqual(record["candidate_count"], 2)
        self.assertEqual(
            record["recommended_fix_bucket"],
            "normalized_stop_field_mapping",
        )

    def test_builds_normalized_but_not_core_mapped_record(self):
        record = build_candidate_coverage_record(
            measurement_alias="RATECON_001",
            field_name="pickup_location",
            stage=COVERAGE_STAGE_CORE_FIELD_MAPPING,
            status=COVERAGE_STATUS_MISSING,
            gap_reason=COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED,
            normalized_field_count=1,
        )

        self.assertEqual(record["normalized_field_count"], 1)
        self.assertEqual(
            record["recommended_fix_bucket"],
            "normalized_to_core_field_mapping",
        )

    def test_aggregate_selects_top_gap_and_next_fix(self):
        aggregate = build_candidate_coverage_aggregate(
            [
                build_candidate_coverage_record(
                    measurement_alias="RATECON_001",
                    field_name="pickup_date",
                    stage=COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
                    status=COVERAGE_STATUS_MISSING,
                    gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                ),
                build_candidate_coverage_record(
                    measurement_alias="RATECON_002",
                    field_name="pickup_date",
                    stage=COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
                    status=COVERAGE_STATUS_MISSING,
                    gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                ),
                build_candidate_coverage_record(
                    measurement_alias="RATECON_003",
                    field_name="delivery_location",
                    stage=COVERAGE_STAGE_NORMALIZED_STOP_FIELD,
                    status=COVERAGE_STATUS_MISSING,
                    gap_reason=COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED,
                    candidate_count=1,
                ),
            ],
            document_count=3,
        )

        self.assertEqual(aggregate["document_count"], 3)
        self.assertEqual(
            aggregate["gap_reason_counts"][COVERAGE_GAP_CANDIDATE_NOT_GENERATED],
            2,
        )
        self.assertEqual(aggregate["top_missing_candidate_fields"], ["pickup_date"])
        self.assertEqual(
            aggregate["recommended_next_fix"],
            "stop_span_date_candidate_generation",
        )

    def test_serialization_contains_no_private_values(self):
        result = build_candidate_coverage_result(
            [
                build_candidate_coverage_record(
                    measurement_alias="RATECON_001",
                    field_name="rate",
                    stage=COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
                    status=COVERAGE_STATUS_MISSING,
                    gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                    evidence_type_counts={"label_value": 1},
                )
            ],
            document_count=1,
        )

        payload = json.loads(json.dumps(result))
        self.assertEqual(
            payload["analysis_version"],
            CANDIDATE_COVERAGE_ANALYSIS_VERSION,
        )
        self.assertFalse(payload["private_values_included"])
        self.assertFalse(payload["raw_text_included"])
        self.assertNotIn("Fake Broker", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
