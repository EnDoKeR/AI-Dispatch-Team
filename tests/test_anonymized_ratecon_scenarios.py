import json
import re
import unittest

from app.market_intelligence.intake.pasted_text_parser_adapter import (
    parse_pasted_text_to_parser_output,
)
from app.market_intelligence.intake.ratecon_core_fields import (
    build_ratecon_core_field_summary,
)
from app.market_intelligence.intake.ratecon_field_diagnostics import (
    detect_ratecon_field_signals,
)
from app.market_intelligence.intake.ratecon_layout_diagnostics import (
    detect_ratecon_layout_shapes,
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
        self.assertLessEqual(len(ANONYMIZED_RATECON_SCENARIOS), 40)

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

    def test_layout_detector_emits_expected_placeholders(self):
        scenarios_with_shapes = [
            scenario
            for scenario in ANONYMIZED_RATECON_SCENARIOS
            if scenario.get("expected_layout_shapes")
        ]

        self.assertGreaterEqual(len(scenarios_with_shapes), 5)

        for scenario in scenarios_with_shapes:
            layout = detect_ratecon_layout_shapes(scenario["text"])

            for category, expected_shapes in scenario["expected_layout_shapes"].items():
                actual_shapes = [
                    item["shape"]
                    for item in layout["shapes_by_category"].get(category, [])
                ]

                for expected_shape in expected_shapes:
                    with self.subTest(
                        scenario=scenario["scenario_id"],
                        category=category,
                        shape=expected_shape,
                    ):
                        self.assertIn(expected_shape, actual_shapes)

    def test_layout_detector_output_omits_fake_values(self):
        for scenario in ANONYMIZED_RATECON_SCENARIOS:
            layout = detect_ratecon_layout_shapes(scenario["text"])
            serialized = json.dumps(layout)

            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertNotIn("FAKE BROKER LLC", serialized)
                self.assertNotIn("FAKE-REF-", serialized)
                self.assertNotIn("Fake City", serialized)
                self.assertNotIn("Fake Town", serialized)
                self.assertNotIn("MC000000", serialized)

    def test_user_table_scenarios_have_expected_core_policy_after_parser_hardening(self):
        scenarios = [
            scenario
            for scenario in ANONYMIZED_RATECON_SCENARIOS
            if "expected_missing_core_fields_after_table_hardening" in scenario
        ]

        self.assertGreaterEqual(len(scenarios), 8)

        for scenario in scenarios:
            parsed = parse_pasted_text_to_parser_output(scenario["text"])
            summary = build_ratecon_core_field_summary(parsed)

            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(
                    set(summary["missing_core_fields"]),
                    set(
                        scenario[
                            "expected_missing_core_fields_after_table_hardening"
                        ]
                    ),
                )
                self.assertIn("loaded_miles", summary["deferred_fields"])
                self.assertEqual(summary["miles_status"], "DEFERRED_GOOGLE_MAPS")


if __name__ == "__main__":
    unittest.main()
