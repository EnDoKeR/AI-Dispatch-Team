import unittest

from app.document_ai import ratecon_rate_money_safety as safety
from app.document_ai.rate_candidate_equivalence import (
    build_rate_candidate_fingerprint,
    normalize_money_amount_for_comparison,
)
from app.document_ai.rate_candidate_forensics import (
    RATE_CATEGORY_DETENTION,
    RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY,
    RATE_CATEGORY_QUICKPAY_DISCOUNT,
    RATE_CATEGORY_TERMS_AMOUNT,
    RATE_CONFLICT_ACCESSORIAL_AS_MAIN_RATE,
    RATE_CONFLICT_LINEHAUL_TOTAL,
    RATE_CONFLICT_MULTIPLE_STRONG_TOTALS,
    RATE_SECTION_RATE_BREAKDOWN,
    RATE_SECTION_RATE_SUMMARY,
    classify_rate_candidate_category,
    classify_rate_candidate_source_section,
    normalize_rate_conflict_reason,
    recommended_rate_fix_bucket,
)
from app.document_ai.rate_conflict_audit import (
    RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT,
    RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS,
    RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED,
    normalize_rate_conflict_audit_reason,
    recommended_rate_conflict_fix_bucket,
)
from app.document_ai.ratecon_candidates import FIELD_ACCESSORIAL_TERM, FIELD_RATE


class RateconRateMoneyCompatibilityPinningTests(unittest.TestCase):
    def _candidate(self, label, value="$2,500.00", confidence=0.9, metadata=None):
        return {
            "field": safety.FIELD_TOTAL_CARRIER_RATE,
            "value": value,
            "normalized_value": value,
            "label": label,
            "confidence": confidence,
            "metadata": metadata or {},
        }

    def test_canonical_rate_money_safety_constants_are_pinned(self):
        self.assertEqual(safety.FIELD_TOTAL_CARRIER_RATE, "total_carrier_rate")
        self.assertEqual(safety.FIELD_ACCESSORIAL_TERM, "accessorial_term")
        self.assertEqual(safety.RATE_MONEY_SAFE, "safe")
        self.assertEqual(safety.RATE_MONEY_RISKY, "risky")
        self.assertEqual(safety.RATE_MONEY_UNSAFE, "unsafe")
        self.assertEqual(safety.RATE_MONEY_UNKNOWN, "unknown")
        self.assertEqual(safety.RATE_SELECTION_ALLOWED, "allowed")
        self.assertEqual(safety.RATE_SELECTION_WEAK_ONLY, "weak_only")
        self.assertEqual(safety.RATE_SELECTION_ABSTAIN, "abstain")
        self.assertEqual(safety.MONEY_CONTEXT_TOTAL_CARRIER_PAY, "total_carrier_pay")
        self.assertEqual(safety.MONEY_CONTEXT_ACCESSORIAL, "accessorial")
        self.assertEqual(safety.MONEY_CONTEXT_FUEL_ADVANCE, "fuel_advance")
        self.assertEqual(safety.MONEY_CONTEXT_QUICKPAY, "quickpay")

    def test_rate_money_context_classification_is_pinned(self):
        cases = [
            ("$2,500.00 Total Carrier Pay", "total_carrier_pay", "safe", ""),
            ("Line Haul $2,500.00", "line_item_rate", "unsafe", "line_item_rate"),
            ("Detention $150.00", "accessorial", "unsafe", "accessorial"),
            (
                "Fuel Advance $500.00",
                "fuel_advance",
                "unsafe",
                "instructions_terms_or_footer_money",
            ),
            (
                "Quick Pay 3%",
                "quickpay",
                "unsafe",
                "instructions_terms_or_footer_money",
            ),
            ("Total: $2,500.00 USD", "unknown", "unknown", "money_context_unknown"),
        ]

        for label, context, rate_safety, reason in cases:
            with self.subTest(label=label):
                candidate = safety.enrich_rate_money_safety(self._candidate(label))
                metadata = candidate["metadata"]
                self.assertEqual(metadata["money_context"], context)
                self.assertEqual(metadata["rate_safety"], rate_safety)
                self.assertEqual(metadata["rate_safety_reason"], reason)

    def test_shadow_abstention_profile_behavior_is_pinned(self):
        adjusted = safety.apply_rate_money_abstention_profile_to_candidates(
            [
                self._candidate("$2,500.00 Total Carrier Pay", "$2,500.00"),
                self._candidate("Line Haul $2,500.00", "$2,500.00"),
                self._candidate("Detention $150.00", "$150.00"),
                self._candidate("Fuel Advance $500.00", "$500.00"),
                self._candidate("Quick Pay 3%", "3%"),
                self._candidate("Total: $2,500.00 USD", "$2,500.00"),
            ]
        )

        first = adjusted[0]
        self.assertEqual(first["field"], safety.FIELD_TOTAL_CARRIER_RATE)
        self.assertEqual(first["confidence"], 0.9)
        self.assertEqual(first["metadata"]["selection_policy"], safety.RATE_SELECTION_ALLOWED)

        for candidate in adjusted[1:]:
            with self.subTest(label=candidate["label"]):
                self.assertEqual(candidate["field"], safety.FIELD_ACCESSORIAL_TERM)
                self.assertEqual(candidate["confidence"], 0.35)
                self.assertEqual(candidate["metadata"]["selection_policy"], safety.RATE_SELECTION_ABSTAIN)
                self.assertTrue(candidate["metadata"]["rate_abstained"])
                self.assertTrue(candidate["metadata"]["rate_demoted_from_total_carrier_rate"])

    def test_rate_candidate_equivalence_money_normalization_is_pinned(self):
        candidate = {
            "field_name": FIELD_RATE,
            "raw_value": "$2,500.00",
            "normalized_value": "",
            "value_type": "total_carrier_pay",
            "label": "Total Carrier Pay",
            "source": "layout",
            "layout_section_role": "RATE_SUMMARY",
        }

        self.assertEqual(normalize_money_amount_for_comparison(candidate), "2500.00")
        self.assertEqual(
            build_rate_candidate_fingerprint(candidate),
            {
                "amount_key": "2500.00",
                "currency": "usd",
                "category": "main_total_carrier_pay",
                "category_family": "main_rate",
                "label": "total_carrier_pay",
                "source": "layout",
                "section": "rate_summary",
            },
        )

    def test_forensics_rate_label_and_context_behavior_is_pinned(self):
        main = {
            "field_name": FIELD_RATE,
            "value_type": "total_carrier_pay",
            "layout_section_role": "RATE_SUMMARY",
        }
        detention = {
            "field_name": FIELD_ACCESSORIAL_TERM,
            "value_type": "detention_pay",
            "layout_section_role": "RATE_BREAKDOWN",
        }
        quickpay = {
            "field_name": FIELD_ACCESSORIAL_TERM,
            "value_type": "quick_pay_discount",
            "layout_section_role": "QUICK_PAY",
        }
        terms = {
            "field_name": FIELD_ACCESSORIAL_TERM,
            "value_type": "unknown_money",
            "layout_section_role": "LEGAL_TERMS",
        }

        self.assertEqual(classify_rate_candidate_category(main), RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY)
        self.assertEqual(classify_rate_candidate_source_section(main), RATE_SECTION_RATE_SUMMARY)
        self.assertEqual(classify_rate_candidate_category(detention), RATE_CATEGORY_DETENTION)
        self.assertEqual(classify_rate_candidate_source_section(detention), RATE_SECTION_RATE_BREAKDOWN)
        self.assertEqual(classify_rate_candidate_category(quickpay), RATE_CATEGORY_QUICKPAY_DISCOUNT)
        self.assertEqual(classify_rate_candidate_category(terms), RATE_CATEGORY_TERMS_AMOUNT)
        self.assertEqual(
            normalize_rate_conflict_reason("accessorial confused with main rate"),
            RATE_CONFLICT_ACCESSORIAL_AS_MAIN_RATE,
        )
        self.assertEqual(
            recommended_rate_fix_bucket(RATE_CONFLICT_MULTIPLE_STRONG_TOTALS),
            "rate_conflict_review_routing",
        )
        self.assertEqual(
            recommended_rate_fix_bucket(RATE_CONFLICT_LINEHAUL_TOTAL),
            "rate_breakdown_total_priority",
        )

    def test_conflict_audit_status_and_fix_bucket_behavior_is_pinned(self):
        self.assertEqual(
            normalize_rate_conflict_audit_reason("linehaul total conflict"),
            RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT,
        )
        self.assertEqual(
            recommended_rate_conflict_fix_bucket(RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT),
            "total_priority_over_linehaul",
        )
        self.assertEqual(
            recommended_rate_conflict_fix_bucket(RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED),
            "selected_rate_core_mapping",
        )
        self.assertEqual(
            recommended_rate_conflict_fix_bucket(RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS),
            "rate_conflict_review_routing",
        )


if __name__ == "__main__":
    unittest.main()
