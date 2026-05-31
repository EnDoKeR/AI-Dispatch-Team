import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.candidate_coverage_analysis import (
    CANDIDATE_COVERAGE_ANALYSIS_VERSION,
    CANDIDATE_COVERAGE_JSON,
    CANDIDATE_COVERAGE_MD,
    COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED,
    COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED,
    COVERAGE_GAP_POLICY_EXCLUDED,
    COVERAGE_GAP_UNKNOWN,
    COVERAGE_STAGE_CORE_FIELD_MAPPING,
    COVERAGE_STAGE_NORMALIZED_STOP_FIELD,
    COVERAGE_STAGE_REVIEW_ROW,
    COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
    COVERAGE_STATUS_CONFLICT,
    COVERAGE_STATUS_MISSING,
    analyze_candidate_coverage_from_rows,
    analyze_candidate_coverage_from_measurement_rows,
    build_candidate_coverage_aggregate,
    build_candidate_coverage_record,
    build_candidate_coverage_result,
    write_candidate_coverage_artifacts,
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

    def test_aggregate_next_fix_ignores_unknown_conflict_rows(self):
        aggregate = build_candidate_coverage_aggregate(
            [
                build_candidate_coverage_record(
                    measurement_alias=f"RATECON_00{index}",
                    field_name="delivery_date",
                    stage=COVERAGE_STAGE_REVIEW_ROW,
                    status=COVERAGE_STATUS_CONFLICT,
                    gap_reason=COVERAGE_GAP_UNKNOWN,
                )
                for index in range(1, 5)
            ]
            + [
                build_candidate_coverage_record(
                    measurement_alias="RATECON_010",
                    field_name="load_number",
                    stage=COVERAGE_STAGE_REVIEW_ROW,
                    status=COVERAGE_STATUS_MISSING,
                    gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                )
            ],
            document_count=5,
        )

        self.assertEqual(
            aggregate["recommended_next_fix"],
            "load_identifier_candidate_generation",
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

    def test_analyzer_classifies_stop_candidate_not_generated(self):
        analysis = analyze_candidate_coverage_from_rows(
            safe_summary_rows=[
                {
                    "document_alias": "RATECON_001",
                    "stop_span_coverage_metrics": {
                        "line_feature_count_by_label_category": {
                            "date": 1,
                            "pickup": 1,
                        },
                        "anchor_count_by_type": {"pickup": 1},
                        "span_count_by_type": {"pickup": 1},
                        "span_field_candidate_count_by_field": {},
                        "normalized_stop_field_count_by_field": {},
                        "core_field_mapping_count_by_field": {},
                    },
                    "field_statuses": [
                        {"field_name": "pickup_date", "status": "missing"}
                    ],
                }
            ],
            core_gap_records=[
                {
                    "measurement_alias": "RATECON_001",
                    "field_name": "pickup_date",
                    "status": "missing",
                    "gap_reason": "no_candidate",
                }
            ],
            stop_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Stop Type": "pickup",
                    "Field Name": "date",
                }
            ],
        )

        record = analysis["records"][0]
        self.assertEqual(record["stage"], COVERAGE_STAGE_SPAN_FIELD_CANDIDATE)
        self.assertEqual(record["gap_reason"], COVERAGE_GAP_CANDIDATE_NOT_GENERATED)
        self.assertEqual(record["review_row_count"], 1)

    def test_analyzer_classifies_candidate_generated_but_not_normalized(self):
        analysis = analyze_candidate_coverage_from_rows(
            safe_summary_rows=[
                {
                    "document_alias": "RATECON_001",
                    "stop_span_coverage_metrics": {
                        "line_feature_count_by_label_category": {
                            "location": 1,
                            "delivery": 1,
                        },
                        "anchor_count_by_type": {"delivery": 1},
                        "span_count_by_type": {"delivery": 1},
                        "span_field_candidate_count_by_field": {"location": 1},
                        "normalized_stop_field_count_by_field": {},
                        "core_field_mapping_count_by_field": {},
                    },
                }
            ],
            core_gap_records=[
                {
                    "measurement_alias": "RATECON_001",
                    "field_name": "delivery_location",
                    "status": "missing",
                    "gap_reason": "no_candidate",
                }
            ],
        )

        record = analysis["records"][0]
        self.assertEqual(record["stage"], COVERAGE_STAGE_NORMALIZED_STOP_FIELD)
        self.assertEqual(
            record["gap_reason"],
            COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED,
        )

    def test_analyzer_classifies_normalized_but_not_core_mapped(self):
        analysis = analyze_candidate_coverage_from_rows(
            safe_summary_rows=[
                {
                    "document_alias": "RATECON_001",
                    "stop_span_coverage_metrics": {
                        "line_feature_count_by_label_category": {
                            "date": 1,
                            "delivery": 1,
                        },
                        "anchor_count_by_type": {"delivery": 1},
                        "span_count_by_type": {"delivery": 1},
                        "span_field_candidate_count_by_field": {"date": 1},
                        "normalized_stop_field_count_by_field": {"date": 1},
                        "core_field_mapping_count_by_field": {},
                    },
                }
            ],
            core_gap_records=[
                {
                    "measurement_alias": "RATECON_001",
                    "field_name": "delivery_date",
                    "status": "missing",
                    "gap_reason": "no_candidate",
                }
            ],
        )

        record = analysis["records"][0]
        self.assertEqual(record["stage"], COVERAGE_STAGE_CORE_FIELD_MAPPING)
        self.assertEqual(record["gap_reason"], COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED)

    def test_optional_core_gap_is_policy_excluded(self):
        analysis = analyze_candidate_coverage_from_rows(
            safe_summary_rows=[{"document_alias": "RATECON_001"}],
            core_gap_records=[
                {
                    "measurement_alias": "RATECON_001",
                    "field_name": "pickup_time",
                    "status": "missing",
                    "gap_reason": "optional_missing_field",
                }
            ],
        )

        self.assertEqual(analysis["records"][0]["gap_reason"], COVERAGE_GAP_POLICY_EXCLUDED)
        self.assertEqual(analysis["records"][0]["status"], "filtered")

    def test_analyzes_from_measurement_rows_without_private_values(self):
        analysis = analyze_candidate_coverage_from_measurement_rows(
            [
                {
                    "document_alias": "RATECON_001",
                    "field_statuses": [
                        {
                            "field_name": "pickup_date",
                            "status": "missing",
                            "candidate_count": 0,
                            "selected_value": "Fake Private Date",
                        }
                    ],
                    "missing_fields": ["pickup_date"],
                    "stop_span_coverage_metrics": {
                        "line_feature_count_by_label_category": {
                            "date": 1,
                            "pickup": 1,
                        },
                        "anchor_count_by_type": {"pickup": 1},
                        "span_count_by_type": {"pickup": 1},
                        "span_field_candidate_count_by_field": {},
                        "normalized_stop_field_count_by_field": {},
                        "core_field_mapping_count_by_field": {},
                    },
                }
            ]
        )

        payload = json.dumps(analysis)
        self.assertIn("pickup_date", payload)
        self.assertNotIn("Fake Private Date", payload)
        self.assertEqual(
            analysis["aggregate"]["recommended_next_fix"],
            "stop_span_date_candidate_generation",
        )

    def test_writes_candidate_coverage_artifacts(self):
        analysis = build_candidate_coverage_result(
            [
                build_candidate_coverage_record(
                    measurement_alias="RATECON_001",
                    field_name="load_number",
                    stage=COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
                    status=COVERAGE_STATUS_MISSING,
                    gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                )
            ],
            document_count=1,
        )

        with tempfile.TemporaryDirectory() as tmp:
            result = write_candidate_coverage_artifacts(
                analysis,
                output_dir=tmp,
                allow_custom_output_dir=True,
            )
            json_text = (Path(tmp) / CANDIDATE_COVERAGE_JSON).read_text(
                encoding="utf-8"
            )
            md_text = (Path(tmp) / CANDIDATE_COVERAGE_MD).read_text(
                encoding="utf-8"
            )

        self.assertIn("candidate_coverage_json", result["paths"])
        self.assertIn("Candidate Coverage Analysis", md_text)
        self.assertIn("load_number", json_text)
        self.assertFalse(result["private_values_printed"])


if __name__ == "__main__":
    unittest.main()
