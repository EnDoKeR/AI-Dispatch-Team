import json
import unittest

from app.document_ai.core_field_gap_analysis import (
    CORE_FIELD_BROKER_MC,
    CORE_FIELD_BROKER_NAME,
    CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED,
    CORE_FIELD_GAP_CONFLICT,
    CORE_FIELD_GAP_NO_CANDIDATE,
    CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED,
    CORE_FIELD_RATE,
    build_core_field_gap_aggregate,
    build_core_field_gap_record,
)


class CoreFieldGapAnalysisTests(unittest.TestCase):
    def test_builds_missing_no_candidate_record(self):
        record = build_core_field_gap_record(
            measurement_alias="RATECON_001",
            field_name=CORE_FIELD_BROKER_NAME,
            status="missing",
            gap_reason=CORE_FIELD_GAP_NO_CANDIDATE,
            candidate_count=0,
            intake_core_blocker=True,
        )

        self.assertEqual(record["field_name"], CORE_FIELD_BROKER_NAME)
        self.assertEqual(record["gap_reason"], CORE_FIELD_GAP_NO_CANDIDATE)
        self.assertTrue(record["intake_core_blocker"])
        self.assertEqual(record["recommended_fix_bucket"], "broker_load_identity_extraction")

    def test_builds_unresolved_record(self):
        record = build_core_field_gap_record(
            measurement_alias="RATECON_001",
            field_name=CORE_FIELD_RATE,
            status="needs_review",
            gap_reason=CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED,
            candidate_count=2,
        )

        self.assertEqual(record["candidate_count"], 2)
        self.assertEqual(
            record["gap_reason"],
            CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED,
        )
        self.assertEqual(record["recommended_fix_bucket"], "rate_resolution_hardening")

    def test_builds_conflict_record(self):
        record = build_core_field_gap_record(
            measurement_alias="RATECON_001",
            field_name=CORE_FIELD_RATE,
            status="conflict",
            gap_reason=CORE_FIELD_GAP_CONFLICT,
            candidate_count=3,
            conflict_count=2,
        )

        self.assertEqual(record["gap_reason"], CORE_FIELD_GAP_CONFLICT)
        self.assertEqual(record["conflict_count"], 2)

    def test_optional_misclassified_record_is_not_intake_blocker(self):
        record = build_core_field_gap_record(
            measurement_alias="RATECON_001",
            field_name=CORE_FIELD_BROKER_MC,
            status="missing",
            gap_reason=CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED,
            intake_core_blocker=False,
            dispatch_decision_blocker=True,
        )

        self.assertFalse(record["intake_core_blocker"])
        self.assertTrue(record["dispatch_decision_blocker"])

    def test_aggregate_selects_top_field_and_target(self):
        aggregate = build_core_field_gap_aggregate(
            [
                build_core_field_gap_record(
                    measurement_alias="RATECON_001",
                    field_name=CORE_FIELD_BROKER_NAME,
                    status="missing",
                    gap_reason=CORE_FIELD_GAP_NO_CANDIDATE,
                ),
                build_core_field_gap_record(
                    measurement_alias="RATECON_002",
                    field_name=CORE_FIELD_BROKER_NAME,
                    status="missing",
                    gap_reason=CORE_FIELD_GAP_NO_CANDIDATE,
                ),
                build_core_field_gap_record(
                    measurement_alias="RATECON_003",
                    field_name=CORE_FIELD_RATE,
                    status="conflict",
                    gap_reason=CORE_FIELD_GAP_CONFLICT,
                ),
            ],
            document_count=3,
        )

        self.assertEqual(aggregate["document_count"], 3)
        self.assertEqual(aggregate["gap_counts_by_field"][CORE_FIELD_BROKER_NAME], 2)
        self.assertEqual(aggregate["top_core_field_gaps"][0], CORE_FIELD_BROKER_NAME)
        self.assertEqual(
            aggregate["recommended_next_target"],
            "broker_load_identity_extraction",
        )

    def test_serialization_contains_no_private_values(self):
        aggregate = build_core_field_gap_aggregate(
            [
                build_core_field_gap_record(
                    measurement_alias="RATECON_001",
                    field_name=CORE_FIELD_BROKER_NAME,
                    status="missing",
                    gap_reason=CORE_FIELD_GAP_NO_CANDIDATE,
                )
            ],
            document_count=1,
        )

        payload = json.dumps(aggregate)
        self.assertIn("RATECON_001", payload)
        self.assertNotIn("Fake Broker", payload)


if __name__ == "__main__":
    unittest.main()
