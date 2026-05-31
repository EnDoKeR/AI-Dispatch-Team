import json
import unittest

from app.document_ai.rate_conflict_audit import (
    RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT,
    RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS,
    RATE_AUDIT_REVISED_ORIGINAL_CONFLICT,
    RATE_AUDIT_SAME_AMOUNT_MULTIPLE_SOURCES,
    RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED,
    build_rate_conflict_audit_aggregate,
    build_rate_conflict_audit_record,
    build_rate_conflict_audit_result,
)


class RateConflictAuditTests(unittest.TestCase):
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
