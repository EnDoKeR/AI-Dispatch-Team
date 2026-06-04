import unittest

from app.document_ai import field_candidate_resolver as resolver
from tests.helpers.ratecon_selected_rate_regression import (
    load_selected_rate_cases,
    run_selected_rate_case,
)


def _candidate(label, *, value="100.00", confidence=0.82, source="native_layout", metadata=None):
    return {
        "field": resolver.FIELD_TOTAL_CARRIER_RATE,
        "label": label,
        "evidence_text": label,
        "value": value,
        "normalized_value": value,
        "confidence": confidence,
        "source": source,
        "metadata": dict(metadata or {}),
    }


class RateconRateRankingPenaltyPinningTests(unittest.TestCase):
    def _adjustments(self, candidate):
        return resolver._profile_adjustments(
            resolver.FIELD_TOTAL_CARRIER_RATE,
            candidate,
            resolver.RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
        )

    def test_total_rate_boosts_are_pinned(self):
        cases = {
            "total_carrier_pay": (
                "Total Carrier Pay: $100.00",
                {"money_context": "total_carrier_pay"},
                [("total_carrier_pay_context", 0.08)],
            ),
            "total_rate": (
                "Total: $100.00",
                {"money_context": "total_rate"},
                [("total_rate_context", 0.06)],
            ),
            "carrier_freight_pay": (
                "Carrier Freight Pay $100.00",
                {"money_context": "carrier_freight_pay"},
                [("carrier_freight_pay_context", 0.04)],
            ),
            "linehaul_total": (
                "Line Haul Pay $100.00",
                {"money_context": "linehaul_total"},
                [("linehaul_total_context", 0.02)],
            ),
        }
        for name, (label, metadata, expected) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(expected, self._adjustments(_candidate(label, metadata=metadata)))

    def test_money_context_penalties_are_pinned(self):
        cases = {
            "line_item": (
                "Line Haul Pay $100.00",
                {"money_context": "line_item_rate", "is_line_item_only": True},
                [("line_item_only_penalty", -0.25)],
            ),
            "deduction": (
                "Rate deduction $100.00",
                {"money_context": "deduction", "is_deduction_or_penalty": True},
                [
                    ("deduction_fee_penalty_context", -0.45),
                    ("deduction_money_context_penalty", -0.42),
                ],
            ),
            "payment_terms": (
                "Payment Terms Net 30 $35 Fee",
                {"money_context": "payment_terms", "is_payment_terms_amount": True},
                [("payment_terms_amount_penalty", -0.40)],
            ),
            "per_unit": (
                "$8.00 Flat",
                {"money_context": "per_unit_rate", "is_per_unit_rate": True},
                [("per_unit_rate_penalty", -0.45)],
            ),
            "accessorial": (
                "Detention $100.00",
                {"money_context": "accessorial", "is_accessorial_only": True},
                [
                    ("accessorial_only_penalty", -0.42),
                    ("accessorial_money_context_penalty", -0.42),
                ],
            ),
        }
        for name, (label, metadata, expected) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(expected, self._adjustments(_candidate(label, metadata=metadata)))

    def test_abstain_and_weak_only_penalties_are_pinned(self):
        abstained = _candidate(
            "Quick Pay 3%",
            metadata={
                "money_context": "quickpay",
                "rate_abstained": True,
                "rate_abstention_reason": "quickpay_unsafe",
            },
        )
        weak_only = _candidate(
            "Carrier Freight Pay $100.00",
            metadata={
                "money_context": "carrier_freight_pay",
                "selection_policy": resolver.RATE_SELECTION_WEAK_ONLY,
                "rate_abstention_reason": "carrier_freight_pay_review",
            },
        )

        self.assertEqual(
            [("quickpay_money_context_penalty", -0.42), ("quickpay_unsafe", -0.60)],
            self._adjustments(abstained),
        )
        self.assertEqual(
            [("carrier_freight_pay_context", 0.04), ("carrier_freight_pay_review", -0.18)],
            self._adjustments(weak_only),
        )

    def test_instruction_region_penalty_is_pinned(self):
        candidate = _candidate(
            "Total $100.00",
            metadata={"money_context": "total_rate", "document_region": "instructions"},
        )

        self.assertEqual(
            [("total_rate_context", 0.06), ("instructions_or_footer_money_penalty", -0.25)],
            self._adjustments(candidate),
        )

    def test_score_trace_and_score_values_are_pinned(self):
        cases = {
            "safe_total": (
                _candidate("Total Carrier Pay: $100.00", metadata={"money_context": "total_carrier_pay"}),
                1.0,
                0.08,
            ),
            "line_item": (
                _candidate(
                    "Line Haul Pay $100.00",
                    metadata={"money_context": "line_item_rate", "is_line_item_only": True},
                ),
                0.72,
                -0.25,
            ),
            "payment_terms": (
                _candidate(
                    "Payment Terms Net 30 $35 Fee",
                    metadata={"money_context": "payment_terms", "is_payment_terms_amount": True},
                ),
                0.49,
                -0.40,
            ),
        }
        for name, (candidate, expected_score, expected_adjustment_total) in cases.items():
            with self.subTest(name=name):
                score = resolver._score(
                    resolver.FIELD_TOTAL_CARRIER_RATE,
                    candidate,
                    {},
                    resolver.RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
                )
                self.assertEqual(expected_score, score)
                self.assertEqual(
                    expected_adjustment_total,
                    candidate["metadata"]["ranking_adjustment_total"],
                )

    def test_selected_rate_fixture_outputs_remain_pinned(self):
        for case in load_selected_rate_cases():
            with self.subTest(case=case["id"]):
                actual = run_selected_rate_case(case)
                expected = dict(case["expected"])
                expected["case_id"] = case["id"]
                expected["known_debt"] = bool(case.get("known_debt"))
                self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
