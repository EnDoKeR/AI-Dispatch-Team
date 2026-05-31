import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.candidate_coverage_analysis import (
    COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED,
    COVERAGE_STAGE_CORE_FIELD_MAPPING,
    COVERAGE_STAGE_REVIEW_ROW,
    COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
    build_candidate_coverage_record,
    build_candidate_coverage_result,
)
from app.document_ai.candidate_coverage_target_selector import (
    CANDIDATE_COVERAGE_TARGET_SELECTION_JSON,
    CANDIDATE_COVERAGE_TARGET_SELECTION_MD,
    TARGET_HUMAN_REVIEW_REQUIRED,
    TARGET_LOAD_IDENTIFIER_CANDIDATE_GENERATION,
    TARGET_NORMALIZED_TO_CORE_FIELD_MAPPING,
    TARGET_RATE_CANDIDATE_GENERATION_OR_RESOLUTION,
    TARGET_STOP_SPAN_DATE_CANDIDATE_GENERATION,
    select_candidate_coverage_target,
    select_candidate_coverage_target_from_dir,
    write_candidate_coverage_target_artifacts,
)


def _analysis(records):
    return build_candidate_coverage_result(records=records, document_count=2)


class CandidateCoverageTargetSelectorTests(unittest.TestCase):
    def test_selects_stop_span_date_when_date_candidate_generation_dominates(self):
        analysis = _analysis(
            [
                build_candidate_coverage_record(
                    measurement_alias="RATECON_001",
                    field_name="pickup_date",
                    stage=COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
                    gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                ),
                build_candidate_coverage_record(
                    measurement_alias="RATECON_002",
                    field_name="delivery_date",
                    stage=COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
                    gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                ),
                build_candidate_coverage_record(
                    measurement_alias="RATECON_003",
                    field_name="load_number",
                    stage=COVERAGE_STAGE_REVIEW_ROW,
                    gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                ),
            ]
        )

        decision = select_candidate_coverage_target(analysis)

        self.assertEqual(
            decision["selected_target"],
            TARGET_STOP_SPAN_DATE_CANDIDATE_GENERATION,
        )
        self.assertEqual(decision["affected_field_count"], 2)
        self.assertEqual(decision["affected_alias_count"], 2)
        self.assertIn("pickup_date", decision["supporting_fields"])
        self.assertFalse(decision["private_values_included"])
        self.assertFalse(decision["raw_text_included"])

    def test_does_not_select_date_when_mapping_is_the_failure(self):
        analysis = _analysis(
            [
                build_candidate_coverage_record(
                    measurement_alias="RATECON_001",
                    field_name="delivery_date",
                    stage=COVERAGE_STAGE_CORE_FIELD_MAPPING,
                    gap_reason=COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED,
                    candidate_count=1,
                    normalized_field_count=1,
                )
            ]
        )

        decision = select_candidate_coverage_target(analysis)

        self.assertEqual(
            decision["selected_target"],
            TARGET_NORMALIZED_TO_CORE_FIELD_MAPPING,
        )

    def test_selects_load_identifier_when_load_number_dominates(self):
        analysis = _analysis(
            [
                build_candidate_coverage_record(
                    measurement_alias=f"RATECON_00{index}",
                    field_name="load_number",
                    stage=COVERAGE_STAGE_REVIEW_ROW,
                    gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                )
                for index in range(1, 4)
            ]
        )

        decision = select_candidate_coverage_target(analysis)

        self.assertEqual(
            decision["selected_target"],
            TARGET_LOAD_IDENTIFIER_CANDIDATE_GENERATION,
        )
        self.assertEqual(decision["supporting_fields"], ["load_number"])

    def test_selects_rate_when_rate_conflict_dominates(self):
        analysis = _analysis(
            [
                build_candidate_coverage_record(
                    measurement_alias=f"RATECON_00{index}",
                    field_name="rate",
                    stage=COVERAGE_STAGE_REVIEW_ROW,
                    status="conflict",
                    gap_reason="unknown",
                )
                for index in range(1, 4)
            ]
        )

        decision = select_candidate_coverage_target(analysis)

        self.assertEqual(
            decision["selected_target"],
            TARGET_RATE_CANDIDATE_GENERATION_OR_RESOLUTION,
        )

    def test_selects_human_review_when_no_clear_target(self):
        decision = select_candidate_coverage_target(
            build_candidate_coverage_result(records=[], document_count=0)
        )

        self.assertEqual(decision["selected_target"], TARGET_HUMAN_REVIEW_REQUIRED)
        self.assertEqual(decision["affected_field_count"], 0)

    def test_serialization_and_artifact_writes_are_safe(self):
        decision = select_candidate_coverage_target(
            _analysis(
                [
                    build_candidate_coverage_record(
                        measurement_alias="RATECON_001",
                        field_name="load_number",
                        stage=COVERAGE_STAGE_REVIEW_ROW,
                        gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                    )
                ]
            )
        )
        payload = json.loads(json.dumps(decision))

        self.assertNotIn("Fake Broker", json.dumps(payload))
        with tempfile.TemporaryDirectory() as tmp:
            result = write_candidate_coverage_target_artifacts(
                decision,
                output_dir=tmp,
                allow_custom_output_dir=True,
            )
            root = Path(tmp)

            self.assertEqual(result["json"], CANDIDATE_COVERAGE_TARGET_SELECTION_JSON)
            self.assertEqual(result["md"], CANDIDATE_COVERAGE_TARGET_SELECTION_MD)
            self.assertTrue((root / CANDIDATE_COVERAGE_TARGET_SELECTION_JSON).exists())
            self.assertTrue((root / CANDIDATE_COVERAGE_TARGET_SELECTION_MD).exists())

    def test_loads_target_selection_from_local_artifact(self):
        analysis = _analysis(
            [
                build_candidate_coverage_record(
                    measurement_alias="RATECON_001",
                    field_name="load_number",
                    stage=COVERAGE_STAGE_REVIEW_ROW,
                    gap_reason=COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
                )
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "candidate_coverage.json").write_text(
                json.dumps(analysis),
                encoding="utf-8",
            )

            decision = select_candidate_coverage_target_from_dir(root)

        self.assertEqual(
            decision["selected_target"],
            TARGET_LOAD_IDENTIFIER_CANDIDATE_GENERATION,
        )


if __name__ == "__main__":
    unittest.main()
