import json
import unittest

from app.market_intelligence.intake.ratecon_field_diagnostics import (
    detect_ratecon_field_signals,
)
from tests.fixtures.legacy_ratecon_label_examples import (
    LEGACY_RATECON_LABEL_EXAMPLES,
)


class LegacyRateConLabelExamplesTests(unittest.TestCase):
    def test_fixtures_import(self):
        self.assertGreaterEqual(len(LEGACY_RATECON_LABEL_EXAMPLES), 5)

    def test_examples_are_json_serializable(self):
        json.dumps(LEGACY_RATECON_LABEL_EXAMPLES)

    def test_examples_use_fake_data_only(self):
        serialized = json.dumps(LEGACY_RATECON_LABEL_EXAMPLES)
        forbidden = [
            "@",
            "gmail",
            "yahoo",
            "hotmail",
            "phone",
            "tel:",
            "555-",
        ]

        self.assertIn("FAKE", serialized)
        self.assertIn("MC000000", serialized)
        self.assertIn("FAKE-REF-001", serialized)

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, serialized.lower())

    def test_fixture_text_contains_legacy_label_styles(self):
        serialized = json.dumps(LEGACY_RATECON_LABEL_EXAMPLES)
        expected_labels = [
            "TRUCKLOAD RATE CONFIRMATION",
            "Shipper Information",
            "Consignee Information",
            "TOTAL",
            "Pick Up Time",
            "Delivery Time",
            "Load #",
            "Carrier Name",
            "Trailer Type/Size",
            "Commodity Description",
            "Total Weight",
        ]

        for label in expected_labels:
            with self.subTest(label=label):
                self.assertIn(label, serialized)

    def test_redacted_diagnostics_detect_expected_labels(self):
        for example in LEGACY_RATECON_LABEL_EXAMPLES:
            with self.subTest(scenario_id=example["scenario_id"]):
                diagnostics = detect_ratecon_field_signals(example["text"])

                for category in example["expected_signal_categories"]:
                    self.assertGreater(
                        diagnostics["signal_counts"][category],
                        0,
                        f"{category} not detected for {example['scenario_id']}",
                    )

    def test_diagnostics_output_does_not_return_fixture_values(self):
        for example in LEGACY_RATECON_LABEL_EXAMPLES:
            with self.subTest(scenario_id=example["scenario_id"]):
                diagnostics = detect_ratecon_field_signals(example["text"])
                serialized = json.dumps(diagnostics)

                self.assertNotIn("FAKE BROKER LLC", serialized)
                self.assertNotIn("FAKE-REF-001", serialized)
                self.assertNotIn("Fake City", serialized)
                self.assertNotIn("FAKE PRODUCT", serialized)


if __name__ == "__main__":
    unittest.main()
