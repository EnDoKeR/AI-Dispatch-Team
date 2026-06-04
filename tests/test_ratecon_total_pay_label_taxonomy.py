import unittest

from app.document_ai import field_candidate_resolver
from app.document_ai import ratecon_candidate_context_features
from app.document_ai import ratecon_candidate_generators
from app.document_ai import ratecon_rate_money_safety as safety
from app.document_ai.field_candidate_resolver import (
    FIELD_TOTAL_CARRIER_RATE,
    RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
    resolve_candidates,
)


class RateconTotalPayLabelTaxonomyTests(unittest.TestCase):
    def _rate_candidate(self, label, value="2500.00", confidence=0.9, metadata=None):
        return {
            "field": safety.FIELD_TOTAL_CARRIER_RATE,
            "value": value,
            "normalized_value": value,
            "label": label,
            "evidence_text": label,
            "source": "native_layout",
            "parser_name": "sanitized_test_fixture",
            "confidence": confidence,
            "metadata": metadata or {},
        }

    def test_canonical_total_pay_label_accessors_are_pinned(self):
        self.assertEqual(
            safety.get_total_pay_positive_labels(),
            (
                "total carrier pay",
                "amount due to carrier",
                "carrier total",
                "estimated rate to truck",
                "estimated rate (to truck)",
                "to truck",
                "agreed rate total",
                "agreed amount total",
                "carrier freight pay",
                "freight pay",
                "linehaul total",
                "line haul total",
                "freight charge total",
                "total cost",
                "total rate-usd",
                "total rate usd",
                "total rate",
            ),
        )
        self.assertEqual(
            safety.get_total_pay_strong_labels(),
            (
                "total carrier pay",
                "total carrier rate",
                "carrier pay",
                "total rate",
                "agreed amount",
            ),
        )
        self.assertEqual(
            safety.get_total_pay_heading_labels(),
            (
                "carrier pay",
                "total rate",
                "agreed amount",
                "linehaul",
                "line haul",
                "total carrier rate",
                "total carrier pay",
                "total charge",
                "freight charge",
                "rate",
            ),
        )
        self.assertEqual(
            safety.get_total_pay_label_types(),
            (
                ("total carrier pay", "total_carrier_pay"),
                ("total carrier rate", "total_carrier_pay"),
                ("carrier pay", "total_carrier_pay"),
                ("total rate", "total_carrier_pay"),
                ("agreed amount", "agreed_amount"),
                ("linehaul", "linehaul"),
                ("line haul", "linehaul"),
                ("total charge", "total_charge"),
                ("freight charge", "total_charge"),
                ("rate", "unknown_money"),
            ),
        )

    def test_compatibility_aliases_equal_canonical_total_pay_taxonomy(self):
        self.assertEqual(
            field_candidate_resolver.RATE_STRONG_LABELS,
            safety.get_total_pay_strong_labels(),
        )
        self.assertEqual(
            ratecon_candidate_generators.STRONG_RATE_LABELS,
            safety.get_total_pay_heading_labels(),
        )
        self.assertEqual(
            ratecon_candidate_generators.STRONG_RATE_LABEL_TYPES,
            safety.get_total_pay_label_types(),
        )

    def test_context_feature_total_pay_markers_preserve_current_behavior(self):
        self.assertEqual(
            ratecon_candidate_context_features._money_context_from_context(
                {},
                "amount due to carrier 2500.00",
            ),
            "total_carrier_pay",
        )
        self.assertEqual(
            ratecon_candidate_context_features._money_context_from_context(
                {},
                "estimated rate 3800.00",
            ),
            "total_rate",
        )
        self.assertEqual(
            ratecon_candidate_context_features._money_context_from_context(
                {},
                "freight charge total 1750.00",
            ),
            "linehaul_total",
        )
        self.assertEqual(
            ratecon_candidate_context_features._money_context_from_context(
                {},
                "per mile 2.50",
            ),
            "line_item_rate",
        )

    def test_total_pay_label_helpers_preserve_current_matching(self):
        true_examples = [
            "Total Carrier Pay: $2,600.00",
            "Carrier Freight Pay: $2,500.00",
            "Estimated Rate (To Truck): $3,800.00",
            "Linehaul Total $3,150.00",
            "Total Rate USD 2,500.00",
        ]
        false_examples = [
            "Total: $2,500.00 USD",
            "Pay Capacity $7,900.00",
            "Net Freight Charges USD 1,750.00",
            "Line Haul Pay $3150.00",
            "Detention $150.00",
            "Quick Pay 3%",
            "Fuel Advance $500.00",
            "$35 Comcheck fee",
            "Tracking $150.00",
            "On Time Delivery $150.00",
        ]

        for text in true_examples:
            with self.subTest(text=text):
                self.assertTrue(safety.is_total_pay_label(text))
        for text in false_examples:
            with self.subTest(text=text):
                self.assertFalse(safety.is_total_pay_label(text))

        self.assertTrue(safety.is_strong_total_pay_context("Total Carrier Pay"))
        self.assertFalse(safety.is_strong_total_pay_context("Carrier Freight Pay"))
        self.assertFalse(safety.is_strong_total_pay_context("Line Haul Pay"))

    def test_sanitized_total_pay_examples_keep_current_safety_classification(self):
        cases = [
            ("Total Carrier Pay: $2,600.00", "total_carrier_pay", "safe", ""),
            (
                "Carrier Freight Pay: $2,500.00",
                "carrier_freight_pay",
                "risky",
                "carrier_freight_pay_requires_no_explicit_total",
            ),
            ("Total: $2,500.00 USD", "unknown", "unknown", "money_context_unknown"),
            ("Pay Capacity $7,900.00", "unknown", "unknown", "money_context_unknown"),
            ("Estimated Rate (To Truck): $3,800.00", "estimated_rate_to_truck", "safe", ""),
            (
                "Net Freight Charges USD 1,750.00",
                "unknown",
                "unknown",
                "money_context_unknown",
            ),
            ("Line Haul Pay $3150.00", "line_item_rate", "unsafe", "line_item_rate"),
        ]

        for label, money_context, rate_safety, reason in cases:
            with self.subTest(label=label):
                candidate = safety.enrich_rate_money_safety(self._rate_candidate(label))
                metadata = candidate["metadata"]
                self.assertEqual(metadata["money_context"], money_context)
                self.assertEqual(metadata["rate_safety"], rate_safety)
                self.assertEqual(metadata["rate_safety_reason"], reason)

    def test_sanitized_non_total_examples_do_not_become_total_pay(self):
        cases = [
            ("Detention $150.00", "accessorial", "unsafe", "accessorial"),
            (
                "Quick Pay 3%",
                "quickpay",
                "unsafe",
                "instructions_terms_or_footer_money",
            ),
            (
                "Fuel Advance $500.00",
                "fuel_advance",
                "unsafe",
                "instructions_terms_or_footer_money",
            ),
            (
                "$35 Comcheck fee",
                "comcheck_fee",
                "unsafe",
                "instructions_terms_or_footer_money",
            ),
            ("Tracking $150.00", "unknown", "unknown", "money_context_unknown"),
            ("On Time Delivery $150.00", "unknown", "unknown", "money_context_unknown"),
        ]

        for label, money_context, rate_safety, reason in cases:
            with self.subTest(label=label):
                candidate = safety.enrich_rate_money_safety(self._rate_candidate(label))
                metadata = candidate["metadata"]
                self.assertEqual(metadata["money_context"], money_context)
                self.assertEqual(metadata["rate_safety"], rate_safety)
                self.assertEqual(metadata["rate_safety_reason"], reason)
                self.assertNotIn(
                    metadata["money_context"],
                    {
                        safety.MONEY_CONTEXT_TOTAL_CARRIER_PAY,
                        safety.MONEY_CONTEXT_TOTAL_RATE,
                        safety.MONEY_CONTEXT_TOTAL_COST,
                        safety.MONEY_CONTEXT_ESTIMATED_RATE_TO_TRUCK,
                        safety.MONEY_CONTEXT_AGREED_RATE_TOTAL,
                    },
                )

    def test_sanitized_rate_selection_still_prefers_safe_total_pay(self):
        candidates = [
            self._rate_candidate(
                "Detention $150.00",
                value="150.00",
                confidence=0.98,
                metadata={"money_context": "accessorial"},
            ),
            self._rate_candidate(
                "Line Haul Pay $3150.00",
                value="3150.00",
                confidence=0.92,
                metadata={"money_context": "line_item_rate"},
            ),
            self._rate_candidate(
                "Quick Pay 3%",
                value="3%",
                confidence=0.96,
                metadata={"money_context": "quickpay"},
            ),
            self._rate_candidate(
                "Total Carrier Pay: $2,600.00",
                value="2600.00",
                confidence=0.82,
                metadata={"money_context": "total_carrier_pay"},
            ),
        ]

        result = resolve_candidates(
            candidates,
            field_names=[FIELD_TOTAL_CARRIER_RATE],
            rate_ranking_profile=RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
        )

        rate = result["resolved_fields"][FIELD_TOTAL_CARRIER_RATE]
        self.assertEqual(rate["value"], "2600.00")
        self.assertEqual(rate["selected_candidate"]["confidence"], 0.82)
        self.assertEqual(rate["selected_candidate"]["source"], "native_layout")
        self.assertEqual(rate["selected_candidate"]["metadata"]["rate_safety"], "safe")


if __name__ == "__main__":
    unittest.main()
