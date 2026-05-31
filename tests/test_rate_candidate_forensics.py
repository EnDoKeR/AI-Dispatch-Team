import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.rate_candidate_forensics import (
    RATE_CATEGORY_ACCESSORIAL,
    RATE_CATEGORY_DETENTION,
    RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY,
    RATE_CATEGORY_QUICKPAY_DISCOUNT,
    RATE_CATEGORY_TERMS_AMOUNT,
    RATE_CONFLICT_ACCESSORIAL_AS_MAIN_RATE,
    RATE_CONFLICT_CANDIDATE_NOT_RESOLVED,
    RATE_CONFLICT_MULTIPLE_STRONG_TOTALS,
    RATE_CONFLICT_QUICKPAY_AS_MAIN_RATE,
    RATE_CONFLICT_TERMS_AMOUNT_AS_MAIN_RATE,
    RATE_FORENSICS_JSON,
    RATE_FORENSICS_MD,
    RATE_SECTION_RATE_SUMMARY,
    RATE_SECTION_TERMS,
    build_rate_forensics_record_from_candidates,
    build_rate_forensics_aggregate,
    build_rate_forensics_record,
    build_rate_forensics_result,
    classify_rate_candidate_category,
    write_rate_forensics_artifacts,
)
from app.document_ai.ratecon_candidates import FIELD_ACCESSORIAL_TERM, FIELD_RATE


class RateCandidateForensicsTests(unittest.TestCase):
    def test_accessorial_conflict_record(self):
        record = build_rate_forensics_record(
            measurement_alias="RATECON_001",
            rate_candidate_count=3,
            accessorial_candidate_count=2,
            conflict_present=True,
            conflict_reason=RATE_CONFLICT_ACCESSORIAL_AS_MAIN_RATE,
            category_counts={RATE_CATEGORY_ACCESSORIAL: 2},
        )

        self.assertEqual(
            record["conflict_reason"],
            RATE_CONFLICT_ACCESSORIAL_AS_MAIN_RATE,
        )
        self.assertEqual(
            record["recommended_fix_bucket"],
            "rate_source_priority_guardrails",
        )
        self.assertFalse(record["money_values_included"])

    def test_quickpay_conflict_record(self):
        record = build_rate_forensics_record(
            measurement_alias="RATECON_002",
            quickpay_candidate_count=1,
            conflict_present=True,
            conflict_reason=RATE_CONFLICT_QUICKPAY_AS_MAIN_RATE,
            category_counts={RATE_CATEGORY_QUICKPAY_DISCOUNT: 1},
        )

        self.assertEqual(record["quickpay_candidate_count"], 1)
        self.assertEqual(
            record["recommended_fix_bucket"],
            "rate_source_priority_guardrails",
        )

    def test_multiple_strong_totals_can_allow_fix_when_shared(self):
        records = [
            build_rate_forensics_record(
                measurement_alias=f"RATECON_00{index}",
                main_rate_candidate_count=2,
                conflict_present=True,
                conflict_reason=RATE_CONFLICT_MULTIPLE_STRONG_TOTALS,
                category_counts={RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY: 2},
                source_section_counts={RATE_SECTION_RATE_SUMMARY: 2},
            )
            for index in range(1, 4)
        ]

        aggregate = build_rate_forensics_aggregate(records, document_count=3)

        self.assertTrue(aggregate["fix_allowed"])
        self.assertEqual(
            aggregate["selected_root_cause"],
            RATE_CONFLICT_MULTIPLE_STRONG_TOTALS,
        )
        self.assertEqual(
            aggregate["recommended_next_action"],
            "rate_conflict_review_routing",
        )

    def test_terms_amount_conflict_category(self):
        result = build_rate_forensics_result(
            [
                build_rate_forensics_record(
                    measurement_alias="RATECON_004",
                    terms_candidate_count=1,
                    conflict_present=True,
                    conflict_reason=RATE_CONFLICT_TERMS_AMOUNT_AS_MAIN_RATE,
                    source_section_counts={RATE_SECTION_TERMS: 1},
                )
            ],
            document_count=1,
        )

        aggregate = result["aggregate"]
        self.assertEqual(
            aggregate["records_by_conflict_reason"][
                RATE_CONFLICT_TERMS_AMOUNT_AS_MAIN_RATE
            ],
            1,
        )

    def test_total_carrier_pay_increments_main_count(self):
        record = build_rate_forensics_record_from_candidates(
            measurement_alias="RATECON_001",
            layout_candidates=[
                {
                    "field_name": FIELD_RATE,
                    "value_type": "total_carrier_pay",
                    "layout_section_role": "RATE_SUMMARY",
                }
            ],
            rate_fusion_result={
                "fused_status": "resolved",
                "selected_candidate_id": "fake_rate",
            },
        )

        self.assertEqual(record["main_rate_candidate_count"], 1)
        self.assertEqual(
            record["category_counts"][RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY],
            1,
        )
        self.assertTrue(record["selected_rate_present"])

    def test_accessorial_quickpay_and_terms_categories_counted(self):
        candidates = [
            {
                "field_name": FIELD_ACCESSORIAL_TERM,
                "value_type": "detention_pay",
                "layout_section_role": "RATE_BREAKDOWN",
            },
            {
                "field_name": FIELD_ACCESSORIAL_TERM,
                "value_type": "quick_pay_discount",
                "layout_section_role": "QUICK_PAY",
            },
            {
                "field_name": FIELD_ACCESSORIAL_TERM,
                "value_type": "unknown_money",
                "layout_section_role": "LEGAL_TERMS",
            },
        ]

        record = build_rate_forensics_record_from_candidates(
            measurement_alias="RATECON_002",
            layout_candidates=candidates,
            rate_fusion_result={"fused_status": "missing"},
        )

        self.assertEqual(record["category_counts"][RATE_CATEGORY_DETENTION], 1)
        self.assertEqual(record["quickpay_candidate_count"], 1)
        self.assertEqual(record["category_counts"][RATE_CATEGORY_TERMS_AMOUNT], 1)
        self.assertEqual(
            record["conflict_reason"],
            RATE_CONFLICT_QUICKPAY_AS_MAIN_RATE,
        )

    def test_conflict_warning_detects_multiple_strong_totals(self):
        record = build_rate_forensics_record_from_candidates(
            measurement_alias="RATECON_003",
            layout_candidates=[
                {
                    "field_name": FIELD_RATE,
                    "value_type": "total_carrier_pay",
                    "layout_section_role": "RATE_SUMMARY",
                },
                {
                    "field_name": FIELD_RATE,
                    "value_type": "total_charge",
                    "layout_section_role": "RATE_SUMMARY",
                },
            ],
            rate_fusion_result={
                "fused_status": "conflict",
                "warning_codes": ["rate_fusion_conflicting_strong_totals"],
            },
        )

        self.assertTrue(record["conflict_present"])
        self.assertEqual(
            record["conflict_reason"],
            RATE_CONFLICT_MULTIPLE_STRONG_TOTALS,
        )

    def test_candidate_generated_but_not_resolved_is_detectable(self):
        record = build_rate_forensics_record_from_candidates(
            measurement_alias="RATECON_004",
            text_candidates=[
                {
                    "field_name": FIELD_RATE,
                    "value_type": "unknown_money",
                    "layout_section_role": "",
                }
            ],
            rate_fusion_result={"fused_status": "missing"},
        )

        self.assertEqual(
            record["conflict_reason"],
            RATE_CONFLICT_CANDIDATE_NOT_RESOLVED,
        )

    def test_classifier_does_not_store_private_amounts(self):
        category = classify_rate_candidate_category(
            {
                "field_name": FIELD_RATE,
                "raw_value": "FAKE_PRIVATE_AMOUNT",
                "value_type": "total_carrier_pay",
            }
        )

        self.assertEqual(category, RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY)

    def test_serialization_contains_no_money_values(self):
        result = build_rate_forensics_result(
            [
                build_rate_forensics_record(
                    measurement_alias="RATECON_001",
                    category_counts={RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY: 1},
                )
            ],
            document_count=1,
        )

        payload = json.dumps(result)

        self.assertNotIn("$", payload)
        self.assertNotIn("2850", payload)
        self.assertFalse(result["private_values_included"])
        self.assertFalse(result["money_values_included"])

    def test_artifact_writes_are_safe(self):
        result = build_rate_forensics_result(
            [
                build_rate_forensics_record(
                    measurement_alias="RATECON_001",
                    category_counts={RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY: 1},
                )
            ],
            document_count=1,
        )

        with tempfile.TemporaryDirectory() as tmp:
            written = write_rate_forensics_artifacts(
                result,
                output_dir=tmp,
                allow_custom_output_dir=True,
            )

            self.assertEqual(written["files"]["rate_forensics_json"], RATE_FORENSICS_JSON)
            self.assertEqual(written["files"]["rate_forensics_md"], RATE_FORENSICS_MD)
            self.assertTrue((Path(tmp) / RATE_FORENSICS_JSON).exists())
            self.assertTrue((Path(tmp) / RATE_FORENSICS_MD).exists())


if __name__ == "__main__":
    unittest.main()
