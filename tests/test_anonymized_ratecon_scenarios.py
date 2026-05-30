import json
import re
import unittest

from app.market_intelligence.intake.ratecon_field_diagnostics import (
    detect_ratecon_field_signals,
)
from tests.fixtures.anonymized_ratecon_scenarios import (
    ANONYMIZED_RATECON_SCENARIOS,
)


REQUIRED_KEYS = {
    "scenario_id",
    "scenario_name",
    "text",
    "expected_present_fields",
    "expected_missing_fields",
    "expected_needs_check_fields",
    "expected_signal_categories",
}


class AnonymizedRateConScenariosTests(unittest.TestCase):
    def test_fixtures_import(self):
        self.assertGreaterEqual(len(ANONYMIZED_RATECON_SCENARIOS), 12)
        self.assertLessEqual(len(ANONYMIZED_RATECON_SCENARIOS), 18)

    def test_each_scenario_has_required_keys(self):
        for scenario in ANONYMIZED_RATECON_SCENARIOS:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertTrue(REQUIRED_KEYS.issubset(scenario))
                self.assertIsInstance(scenario["text"], str)
                self.assertTrue(scenario["text"].strip())
                self.assertIsInstance(scenario["expected_present_fields"], list)
                self.assertIsInstance(scenario["expected_missing_fields"], list)
                self.assertIsInstance(scenario["expected_needs_check_fields"], list)
                self.assertIsInstance(scenario["expected_signal_categories"], list)

    def test_scenarios_are_json_serializable(self):
        json.dumps(ANONYMIZED_RATECON_SCENARIOS)

    def test_scenarios_use_fake_placeholders_only(self):
        serialized = json.dumps(ANONYMIZED_RATECON_SCENARIOS)
        lower = serialized.lower()

        self.assertIn("fake", lower)
        self.assertIn("mc000000", lower)
        self.assertIn("fake-ref-", lower)

        forbidden_terms = [
            "gmail",
            "yahoo",
            "hotmail",
            "outlook",
            "private",
            "ratecon_001",
            "phone",
            "tel:",
            "dispatch@",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, lower)

        self.assertIsNone(re.search(r"\b\d{3}[-.]\d{3}[-.]\d{4}\b", serialized))
        self.assertIsNone(
            re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", serialized, re.I)
        )

    def test_diagnostics_detect_expected_signal_categories(self):
        for scenario in ANONYMIZED_RATECON_SCENARIOS:
            diagnostics = detect_ratecon_field_signals(scenario["text"])

            for category in scenario["expected_signal_categories"]:
                with self.subTest(
                    scenario=scenario["scenario_id"],
                    category=category,
                ):
                    self.assertGreater(
                        diagnostics["signal_counts"][category],
                        0,
                    )

    def test_diagnostics_output_does_not_return_fixture_values(self):
        for scenario in ANONYMIZED_RATECON_SCENARIOS:
            diagnostics = detect_ratecon_field_signals(scenario["text"])
            serialized = json.dumps(diagnostics)

            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertNotIn("FAKE BROKER LLC", serialized)
                self.assertNotIn("FAKE-REF-", serialized)
                self.assertNotIn("Fake City", serialized)
                self.assertNotIn("Fake Town", serialized)


if __name__ == "__main__":
    unittest.main()
