import json
import unittest

from app.document_ai.rate_conflict_audit import (
    RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT,
    RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS,
    RATE_AUDIT_REVISED_ORIGINAL_CONFLICT,
    RATE_AUDIT_SAME_AMOUNT_MULTIPLE_SOURCES,
    RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED,
    build_rate_conflict_audit_record_from_candidates,
    build_rate_conflict_audit_aggregate,
    build_rate_conflict_audit_record,
    build_rate_conflict_audit_result,
)
from app.document_ai.ratecon_candidates import FIELD_ACCESSORIAL_TERM, FIELD_RATE


class RateConflictAuditTests(unittest.TestCase):
    def _candidate(
        self,
        value,
        candidate_id="rate_1",
        field_name=FIELD_RATE,
        value_type="total_carrier_pay",
        label="Total Carrier Pay",
        confidence="HIGH",
    ):
        return {
            "candidate_id": candidate_id,
            "field_name": field_name,
            "normalized_value": value,
            "raw_value": value,
            "value_type": value_type,
            "label": label,
            "confidence": confidence,
        }

    def test_equivalent_same_amount_record(self):
        record = build_rate_conflict_audit_record(
            measurement_alias="RATECON_001",
            rate_candidate_count=3,
            main_rate_candidate_count=3,
            equivalent_candidate_group_count=1,
            conflict_reason=RATE_AUDIT_SAME_AMOUNT_MULTIPLE_SOURCES,
        )

        self.assertEqual(record["equivalent_candidate_group_count"], 1)
        self.assertEqual(
            record["recommended_fix_bucket"],
            "equivalent_candidate_dedupe_and_confidence_reinforcement",
        )
        self.assertFalse(record["money_values_included"])

    def test_multiple_different_strong_totals_record(self):
        record = build_rate_conflict_audit_record(
            measurement_alias="RATECON_002",
            main_rate_candidate_count=2,
            different_strong_total_count=2,
            conflict_present=True,
            review_required=True,
            conflict_reason=RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS,
        )

        self.assertTrue(record["review_required"])
        self.assertEqual(
            record["recommended_fix_bucket"],
            "rate_conflict_review_routing",
        )

    def test_aggregate_selects_shared_multiple_strong_totals(self):
        records = [
            build_rate_conflict_audit_record(
                measurement_alias=f"RATECON_00{index}",
                conflict_present=True,
                conflict_reason=RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS,
            )
            for index in range(1, 4)
        ]

        aggregate = build_rate_conflict_audit_aggregate(records, document_count=3)

        self.assertTrue(aggregate["fix_allowed"])
        self.assertEqual(
            aggregate["selected_root_cause"],
            RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS,
        )
        self.assertEqual(
            aggregate["recommended_next_action"],
            "rate_conflict_review_routing",
        )

    def test_linehaul_revised_and_core_mapping_reasons(self):
        reasons = {
            RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT: "total_priority_over_linehaul",
            RATE_AUDIT_REVISED_ORIGINAL_CONFLICT: "revised_current_priority",
            RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED: "selected_rate_core_mapping",
        }

        for reason, expected_bucket in reasons.items():
            with self.subTest(reason=reason):
                record = build_rate_conflict_audit_record(conflict_reason=reason)
                self.assertEqual(record["recommended_fix_bucket"], expected_bucket)

    def test_fake_equivalent_candidates_produce_equivalent_group(self):
        record = build_rate_conflict_audit_record_from_candidates(
            measurement_alias="RATECON_001",
            text_candidates=[self._candidate("1200.00", candidate_id="text")],
            layout_candidates=[self._candidate("1200.00", candidate_id="layout")],
            rate_fusion_result={"fused_status": "resolved", "selected_candidate_id": "text"},
            resolution_result={
                "resolutions": [
                    {"field_name": FIELD_RATE, "status": "resolved"},
                ]
            },
        )

        self.assertEqual(record["equivalent_candidate_group_count"], 1)
        self.assertEqual(record["different_strong_total_count"], 0)
        self.assertTrue(record["core_rate_mapped"])

    def test_fake_different_totals_produce_multiple_strong_totals(self):
        record = build_rate_conflict_audit_record_from_candidates(
            measurement_alias="RATECON_002",
            layout_candidates=[
                self._candidate("1200.00", candidate_id="a"),
                self._candidate("1300.00", candidate_id="b"),
            ],
            rate_fusion_result={
                "fused_status": "conflict",
                "review_required": True,
                "warning_codes": ["rate_fusion_conflicting_strong_totals"],
            },
        )

        self.assertEqual(record["different_strong_total_count"], 2)
        self.assertEqual(
            record["conflict_reason"],
            RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS,
        )

    def test_fake_linehaul_total_conflict_detected(self):
        record = build_rate_conflict_audit_record_from_candidates(
            measurement_alias="RATECON_003",
            layout_candidates=[
                self._candidate(
                    "1200.00",
                    candidate_id="linehaul",
                    value_type="linehaul",
                    label="Linehaul",
                ),
                self._candidate("1300.00", candidate_id="total"),
            ],
            rate_fusion_result={"fused_status": "conflict", "review_required": True},
        )

        self.assertEqual(record["linehaul_candidate_count"], 1)
        self.assertEqual(record["conflict_reason"], RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT)

    def test_fake_revised_original_detected(self):
        record = build_rate_conflict_audit_record_from_candidates(
            measurement_alias="RATECON_004",
            layout_candidates=[
                self._candidate(
                    "1200.00",
                    candidate_id="original",
                    label="Original Total",
                ),
                self._candidate(
                    "1300.00",
                    candidate_id="revised",
                    label="Revised Total",
                ),
            ],
            rate_fusion_result={"fused_status": "conflict", "review_required": True},
        )

        self.assertEqual(record["revised_current_candidate_count"], 1)
        self.assertEqual(record["original_previous_candidate_count"], 1)
        self.assertEqual(record["conflict_reason"], RATE_AUDIT_REVISED_ORIGINAL_CONFLICT)

    def test_fake_selected_not_core_mapped_detected(self):
        record = build_rate_conflict_audit_record_from_candidates(
            measurement_alias="RATECON_005",
            layout_candidates=[self._candidate("1200.00")],
            rate_fusion_result={
                "fused_status": "resolved",
                "selected_candidate_id": "rate_1",
            },
            resolution_result={
                "resolutions": [
                    {"field_name": FIELD_RATE, "status": "needs_review"},
                ]
            },
        )

        self.assertTrue(record["selected_rate_present"])
        self.assertFalse(record["core_rate_mapped"])
        self.assertEqual(
            record["conflict_reason"],
            RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED,
        )

    def test_accessorial_counted_without_money_values(self):
        record = build_rate_conflict_audit_record_from_candidates(
            measurement_alias="RATECON_006",
            layout_candidates=[
                self._candidate(
                    "250.00",
                    field_name=FIELD_ACCESSORIAL_TERM,
                    value_type="detention_pay",
                    label="Detention",
                )
            ],
            rate_fusion_result={"fused_status": "missing"},
        )
        payload = json.dumps(record)

        self.assertEqual(record["accessorial_candidate_count"], 1)
        self.assertNotIn("250", payload)

    def test_serialization_excludes_money_values(self):
        result = build_rate_conflict_audit_result(
            [
                build_rate_conflict_audit_record(
                    measurement_alias="RATECON_001",
                    conflict_reason=RATE_AUDIT_SAME_AMOUNT_MULTIPLE_SOURCES,
                    equivalent_candidate_group_count=1,
                )
            ],
            document_count=1,
        )

        payload = json.dumps(result)

        self.assertNotIn("$", payload)
        self.assertNotIn("2850", payload)
        self.assertFalse(result["private_values_included"])
        self.assertFalse(result["money_values_included"])


if __name__ == "__main__":
    unittest.main()
