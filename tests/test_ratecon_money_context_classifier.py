import unittest

from app.document_ai import ratecon_candidate_context_features
from app.document_ai import ratecon_rate_money_safety as safety
from tests.helpers.ratecon_selected_rate_regression import run_selected_rate_cases


class RateconMoneyContextClassifierTests(unittest.TestCase):
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

    def test_canonical_classifier_api_is_pinned(self):
        result = safety.classify_money_context("Total Carrier Pay: $2,600.00")
        self.assertIsInstance(result, safety.MoneyContextClassification)
        self.assertEqual(result.money_context, "total_carrier_pay")
        self.assertEqual(result.document_region, "payment_summary")
        self.assertEqual(result.rate_safety, "safe")
        self.assertEqual(result.rate_safety_reason, "")

        labels = safety.get_money_context_classifier_labels()
        self.assertIn("safe_total_contexts", labels)
        self.assertIn("negative_contexts", labels)
        self.assertIn("line_item_contexts", labels)
        self.assertEqual(
            labels["line_item_contexts"],
            ("linehaul_total", "line_item_rate", "per_unit_rate"),
        )

    def test_rate_candidate_classifier_matches_enrichment_metadata(self):
        cases = [
            "Total Carrier Pay: $2,600.00",
            "Carrier Freight Pay: $2,500.00",
            "Line Haul Pay $3150.00",
            "Detention $150.00",
            "Quick Pay 3%",
            "Fuel Advance $500.00",
            "$35 Comcheck fee",
            "Total: $2,500.00 USD",
        ]

        for label in cases:
            with self.subTest(label=label):
                candidate = self._rate_candidate(label)
                result = safety.classify_rate_candidate_context(candidate)
                metadata = safety.enrich_rate_money_safety(candidate)["metadata"]
                self.assertEqual(result.money_context, metadata["money_context"])
                self.assertEqual(result.document_region, metadata["document_region"])
                self.assertEqual(result.rate_safety, metadata["rate_safety"])
                self.assertEqual(result.rate_safety_reason, metadata["rate_safety_reason"])

    def test_total_and_line_item_context_examples_are_current_behavior(self):
        cases = [
            ("Total Carrier Pay: $2,600.00", "total_carrier_pay", "safe", True, False),
            ("Carrier Freight Pay: $2,500.00", "carrier_freight_pay", "risky", False, False),
            ("Total: $2,500.00 USD", "unknown", "unknown", False, False),
            ("Line Haul Pay $3150.00", "line_item_rate", "unsafe", False, True),
            ("Estimated Rate (To Truck): $3,800.00", "estimated_rate_to_truck", "safe", True, False),
            ("Net Freight Charges USD 1,750.00", "unknown", "unknown", False, False),
            ("Total Cost USD 1,750.00", "total_cost", "safe", True, False),
            ("Pay Capacity $7,900.00", "unknown", "unknown", False, False),
            ("$8.00 Flat 1.00 $8.00", "unknown", "unknown", False, False),
            ("$6.38 PER 50LBS BAG 900.00 $5,742.00", "unknown", "unknown", False, False),
            ("Line Haul Flat 1.0000 $2,500.00", "line_item_rate", "unsafe", False, True),
        ]

        for text, money_context, rate_safety, safe_total, line_item in cases:
            with self.subTest(text=text):
                result = safety.classify_money_context(text)
                self.assertEqual(result.money_context, money_context)
                self.assertEqual(result.rate_safety, rate_safety)
                self.assertEqual(
                    safety.is_safe_total_rate_context(text),
                    safe_total,
                )
                self.assertEqual(
                    safety.is_line_item_money_context(text),
                    line_item,
                )

    def test_noise_payment_and_billing_context_examples_are_current_behavior(self):
        cases = [
            ("Detention $150.00", "accessorial", "unsafe", True, False),
            ("Quick Pay 3%", "quickpay", "unsafe", True, True),
            ("1 Day Quick Pay 5%", "quickpay", "unsafe", True, True),
            ("Fuel Advance $500.00", "fuel_advance", "unsafe", True, False),
            ("$35 Comcheck fee", "comcheck_fee", "unsafe", True, False),
            ("Tracking $150.00", "unknown", "unknown", False, False),
            ("On Time Paperwork $150.00", "unknown", "unknown", False, False),
            ("On Time Delivery $150.00", "unknown", "unknown", False, False),
            ("Lumper $250.00", "accessorial", "unsafe", True, False),
            ("Gate Fee $50.00", "fee", "unsafe", True, False),
            ("TONU $150.00", "penalty", "unsafe", True, False),
            ("Rate deduction $250.00", "deduction", "unsafe", True, False),
            ("MacroPoint tracking $150.00", "unknown", "unknown", False, False),
            ("Detention rate $35/hr", "accessorial", "unsafe", True, False),
            ("Payment terms are net 30 days", "payment_terms_amount", "unsafe", True, True),
            ("Invoices must be sent to billing@example.test", "unknown", "unknown", False, False),
            ("Quick Pay email or fax listed below", "quickpay", "unsafe", True, True),
            ("All accessorial charges must be pre-approved", "accessorial", "unsafe", True, False),
            (
                "There is a $35 fee to each Comcheck issued for fuel and final pay",
                "comcheck_fee",
                "unsafe",
                True,
                False,
            ),
        ]

        for text, money_context, rate_safety, unsafe, billing_noise in cases:
            with self.subTest(text=text):
                result = safety.classify_money_context(text)
                self.assertEqual(result.money_context, money_context)
                self.assertEqual(result.rate_safety, rate_safety)
                self.assertEqual(safety.is_unsafe_money_context(text), unsafe)
                self.assertEqual(safety.is_billing_noise_context(text), billing_noise)
                if billing_noise:
                    self.assertTrue(safety.is_payment_instruction_context(text))

    def test_context_feature_wrapper_preserves_legacy_classifier_debt(self):
        cases = [
            ("comcheck 500.00", "fuel_advance"),
            ("tracking hold 150.00", "penalty"),
            ("chargeback 250.00", "deduction"),
            ("detention 150.00", "accessorial"),
            ("payment terms net 30", "payment_terms_amount"),
            ("amount due to carrier 2500.00", "total_carrier_pay"),
            ("estimated rate 3800.00", "total_rate"),
            ("freight charge total 1750.00", "linehaul_total"),
            ("per mile 2.50", "line_item_rate"),
        ]

        for context, expected in cases:
            with self.subTest(context=context):
                self.assertEqual(
                    safety.classify_context_feature_money_context({}, context),
                    expected,
                )
                self.assertEqual(
                    ratecon_candidate_context_features._money_context_from_context({}, context),
                    expected,
                )

    def test_selected_rate_regression_harness_still_matches_expected_outputs(self):
        results = run_selected_rate_cases()
        self.assertEqual(12, len(results))
        self.assertEqual(4, sum(1 for result in results if result["known_debt"]))
        self.assertTrue(all(result["case_id"] for result in results))


if __name__ == "__main__":
    unittest.main()
