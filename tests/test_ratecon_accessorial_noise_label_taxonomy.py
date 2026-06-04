import unittest

from app.document_ai import field_candidate_resolver
from app.document_ai import layout_rate_candidates
from app.document_ai import ratecon_candidate_context_features
from app.document_ai import ratecon_candidate_generators
from app.document_ai import ratecon_ocr_candidate_policy
from app.document_ai import ratecon_rate_money_safety as safety
from app.document_ai.field_candidate_resolver import (
    FIELD_TOTAL_CARRIER_RATE,
    RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
    resolve_candidates,
)


class RateconAccessorialNoiseLabelTaxonomyTests(unittest.TestCase):
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

    def test_canonical_accessorial_noise_label_accessors_are_pinned(self):
        self.assertEqual(
            safety.get_accessorial_charge_labels(),
            (
                "detention",
                "layover",
                "lumper",
                "tonu",
                "quick pay",
                "fuel surcharge",
                "accessorial",
                "fee",
                "penalty",
                "deduction",
            ),
        )
        self.assertEqual(
            safety.get_accessorial_label_types(),
            (
                ("detention", "detention_pay"),
                ("layover", "layover_pay"),
                ("lumper", "lumper_pay"),
                ("tonu", "TONU_pay"),
                ("truck order not used", "TONU_pay"),
                ("quick pay", "quick_pay_discount"),
                ("fuel surcharge", "accessorial"),
                ("accessorial", "accessorial"),
                ("fee", "accessorial"),
                ("penalty", "deduction"),
                ("deduction", "deduction"),
            ),
        )
        self.assertEqual(
            safety.get_layout_accessorial_label_types(),
            (
                ("tracking bonus", "tracking_bonus"),
                ("on time bonus", "on_time_bonus"),
                ("detention", "detention_pay"),
                ("tonu", "TONU_pay"),
                ("truck order not used", "TONU_pay"),
                ("deduction", "deduction"),
                ("penalty", "deduction"),
                ("quick pay", "quick_pay_discount"),
                ("discount", "quick_pay_discount"),
                ("accessorial", "accessorial"),
                ("fee", "accessorial"),
            ),
        )

    def test_canonical_noise_marker_accessors_are_pinned(self):
        self.assertEqual(safety.get_quick_pay_noise_labels(), ("quickpay", "quick pay"))
        self.assertEqual(
            safety.get_rate_deduction_labels(),
            ("deduction", "deduct", "chargeback"),
        )
        self.assertEqual(
            safety.get_fee_penalty_noise_labels(),
            ("penalty", "tonu", "truck order not used", "late fee"),
        )
        self.assertEqual(
            safety.get_billing_instruction_noise_labels(),
            ("payment terms", "net 30", "net30", "days to pay"),
        )
        self.assertEqual(
            safety.get_rate_negative_labels(),
            (
                "fuel",
                "detention",
                "layover",
                "lumper",
                "quickpay",
                "quick pay",
                "deduction",
                "penalty",
                "tonu",
                "insurance",
                "advance",
                "accessorial",
            ),
        )
        self.assertEqual(
            safety.get_money_context_noise_markers(),
            (
                "quickpay",
                "quick pay",
                "comcheck",
                "com check",
                "tracking hold",
                "tracking fee",
                "holdback",
                "fuel advance",
                "advance",
                "deduction",
                "deduct",
                "chargeback",
                "penalty",
                "tonu",
                "truck order not used",
                "late fee",
                "detention",
                "layover",
                "lumper",
                "accessorial",
                "payment terms",
                "net 30",
                "net30",
                "days to pay",
            ),
        )

    def test_compatibility_aliases_equal_canonical_accessorial_taxonomy(self):
        self.assertEqual(
            field_candidate_resolver.RATE_NEGATIVE_LABELS,
            safety.get_rate_negative_labels(),
        )
        self.assertEqual(
            ratecon_candidate_generators.ACCESSORIAL_LABELS,
            safety.get_accessorial_charge_labels(),
        )
        self.assertEqual(
            ratecon_candidate_generators.ACCESSORIAL_LABEL_TYPES,
            safety.get_accessorial_label_types(),
        )
        self.assertEqual(
            layout_rate_candidates.ACCESSORIAL_LABELS,
            safety.get_layout_accessorial_label_types(),
        )
        self.assertEqual(
            ratecon_ocr_candidate_policy._UNSAFE_OCR_RATE_CONTEXTS,
            safety.get_ocr_unsafe_rate_contexts(),
        )

    def test_context_feature_accessorial_noise_markers_preserve_current_behavior(self):
        self.assertEqual(
            ratecon_candidate_context_features._money_context_from_context(
                {},
                "comcheck 500.00",
            ),
            "fuel_advance",
        )
        self.assertEqual(
            ratecon_candidate_context_features._money_context_from_context(
                {},
                "tracking hold 150.00",
            ),
            "penalty",
        )
        self.assertEqual(
            ratecon_candidate_context_features._money_context_from_context(
                {},
                "chargeback 250.00",
            ),
            "deduction",
        )
        self.assertEqual(
            ratecon_candidate_context_features._money_context_from_context(
                {},
                "detention 150.00",
            ),
            "accessorial",
        )
        self.assertEqual(
            ratecon_candidate_context_features._money_context_from_context(
                {},
                "payment terms net 30",
            ),
            "payment_terms_amount",
        )

    def test_accessorial_noise_helpers_preserve_current_matching(self):
        accessorial_examples = [
            "Detention $150.00",
            "Lumper $250.00",
            "Detention rate $35/hr",
        ]
        deduction_fee_examples = [
            "Fuel Advance $500.00",
            "$35 Comcheck fee",
            "Gate Fee $50.00",
            "TONU $150.00",
            "Late fee $150.00",
            "Rate deduction $250.00",
        ]
        quick_billing_examples = [
            "Quick Pay 3%",
            "1 Day Quick Pay 5%",
            "7 Day Quick Pay 3%",
            "Payment Terms Net 30",
        ]
        current_debt_unknown_examples = [
            "Tracking $150.00",
            "On Time Paperwork $150.00",
            "On Time Delivery $150.00",
            "MacroPoint tracking $150.00",
        ]

        for text in accessorial_examples:
            with self.subTest(text=text):
                self.assertTrue(safety.is_accessorial_money_context(text))
                self.assertTrue(safety.is_non_total_money_noise_context(text))
        for text in deduction_fee_examples:
            with self.subTest(text=text):
                self.assertTrue(safety.is_rate_deduction_or_fee_context(text))
                self.assertTrue(safety.is_non_total_money_noise_context(text))
        for text in quick_billing_examples:
            with self.subTest(text=text):
                self.assertTrue(safety.is_quick_pay_or_billing_noise_context(text))
                self.assertTrue(safety.is_non_total_money_noise_context(text))
        for text in current_debt_unknown_examples:
            with self.subTest(text=text):
                self.assertFalse(safety.is_accessorial_money_context(text))
                self.assertFalse(safety.is_rate_deduction_or_fee_context(text))
                self.assertFalse(safety.is_quick_pay_or_billing_noise_context(text))
                self.assertFalse(safety.is_non_total_money_noise_context(text))

    def test_sanitized_noise_examples_keep_current_safety_classification(self):
        cases = [
            ("Detention $150.00", "accessorial", "unsafe", "accessorial"),
            ("Quick Pay 3%", "quickpay", "unsafe", "instructions_terms_or_footer_money"),
            ("1 Day Quick Pay 5%", "quickpay", "unsafe", "instructions_terms_or_footer_money"),
            ("7 Day Quick Pay 3%", "quickpay", "unsafe", "instructions_terms_or_footer_money"),
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
            ("On Time Paperwork $150.00", "unknown", "unknown", "money_context_unknown"),
            ("On Time Delivery $150.00", "unknown", "unknown", "money_context_unknown"),
            ("Lumper $250.00", "accessorial", "unsafe", "accessorial"),
            ("Gate Fee $50.00", "fee", "unsafe", "fee"),
            ("TONU $150.00", "penalty", "unsafe", "penalty"),
            ("Late fee $150.00", "penalty", "unsafe", "penalty"),
            ("Rate deduction $250.00", "deduction", "unsafe", "deduction"),
            ("MacroPoint tracking $150.00", "unknown", "unknown", "money_context_unknown"),
            ("Detention rate $35/hr", "accessorial", "unsafe", "accessorial"),
        ]

        for label, money_context, rate_safety, reason in cases:
            with self.subTest(label=label):
                candidate = safety.enrich_rate_money_safety(self._rate_candidate(label))
                metadata = candidate["metadata"]
                self.assertEqual(metadata["money_context"], money_context)
                self.assertEqual(metadata["rate_safety"], rate_safety)
                self.assertEqual(metadata["rate_safety_reason"], reason)

    def test_total_pay_examples_do_not_become_accessorial_noise(self):
        cases = [
            ("Total Carrier Pay: $2,600.00", "total_carrier_pay", "safe", ""),
            (
                "Carrier Freight Pay: $2,500.00",
                "carrier_freight_pay",
                "risky",
                "carrier_freight_pay_requires_no_explicit_total",
            ),
            ("Total: $2,500.00 USD", "unknown", "unknown", "money_context_unknown"),
            ("Line Haul Pay $3150.00", "line_item_rate", "unsafe", "line_item_rate"),
            ("Estimated Rate (To Truck): $3,800.00", "estimated_rate_to_truck", "safe", ""),
            (
                "Net Freight Charges USD 1,750.00",
                "unknown",
                "unknown",
                "money_context_unknown",
            ),
        ]

        for label, money_context, rate_safety, reason in cases:
            with self.subTest(label=label):
                candidate = safety.enrich_rate_money_safety(self._rate_candidate(label))
                metadata = candidate["metadata"]
                self.assertEqual(metadata["money_context"], money_context)
                self.assertEqual(metadata["rate_safety"], rate_safety)
                self.assertEqual(metadata["rate_safety_reason"], reason)
                self.assertFalse(safety.is_non_total_money_noise_context(label))

    def test_sanitized_rate_selection_still_rejects_noise_and_selects_total(self):
        candidates = [
            self._rate_candidate(
                "Detention $150.00",
                value="150.00",
                confidence=0.98,
                metadata={"money_context": "accessorial"},
            ),
            self._rate_candidate(
                "Quick Pay 3%",
                value="3%",
                confidence=0.96,
                metadata={"money_context": "quickpay"},
            ),
            self._rate_candidate(
                "Tracking Fee $150.00",
                value="150.00",
                confidence=0.95,
                metadata={"money_context": "tracking_hold"},
            ),
            self._rate_candidate(
                "Fuel Advance $500.00",
                value="500.00",
                confidence=0.94,
                metadata={"money_context": "fuel_advance"},
            ),
            self._rate_candidate(
                "Line Haul Pay $3150.00",
                value="3150.00",
                confidence=0.92,
                metadata={"money_context": "line_item_rate"},
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
