import json
import unittest

from app.market_intelligence.decision_engine.risk_flags import is_known_risk_flag
from tests.fixtures.decision_engine_scenarios import DECISION_ENGINE_SCENARIOS


REQUIRED_SCENARIO_KEYS = {
    "scenario_id",
    "scenario_name",
    "input_signals",
    "expected_decision",
    "expected_category",
    "expected_risk_flags",
    "expected_missing_fields",
    "expected_needs_check_fields",
    "expected_review_reasons",
    "expected_block_reasons",
    "expected_approval_required",
}


class DecisionEngineScenariosTest(unittest.TestCase):
    def test_fixture_count_is_safe(self):
        self.assertGreaterEqual(len(DECISION_ENGINE_SCENARIOS), 8)
        self.assertLessEqual(len(DECISION_ENGINE_SCENARIOS), 12)

    def test_each_scenario_has_required_keys(self):
        for scenario in DECISION_ENGINE_SCENARIOS:
            with self.subTest(scenario=scenario.get("scenario_id", "")):
                self.assertEqual(set(scenario.keys()), REQUIRED_SCENARIO_KEYS)
                self.assertIsInstance(scenario["scenario_id"], str)
                self.assertIsInstance(scenario["scenario_name"], str)
                self.assertIsInstance(scenario["input_signals"], dict)
                self.assertIsInstance(scenario["expected_risk_flags"], list)
                self.assertIsInstance(scenario["expected_missing_fields"], list)
                self.assertIsInstance(scenario["expected_needs_check_fields"], list)
                self.assertIsInstance(scenario["expected_review_reasons"], list)
                self.assertIsInstance(scenario["expected_block_reasons"], list)
                self.assertIsInstance(scenario["expected_approval_required"], bool)

    def test_expected_decisions_are_supported(self):
        allowed_decisions = {"MATCH", "REVIEW_ONCE", "BLOCK", "NO_ACTION"}

        for scenario in DECISION_ENGINE_SCENARIOS:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertIn(scenario["expected_decision"], allowed_decisions)

    def test_risk_flags_are_known(self):
        for scenario in DECISION_ENGINE_SCENARIOS:
            with self.subTest(scenario=scenario["scenario_id"]):
                for flag in scenario["expected_risk_flags"]:
                    self.assertTrue(is_known_risk_flag(flag), flag)

    def test_scenarios_are_json_serializable(self):
        json.dumps(DECISION_ENGINE_SCENARIOS)

    def test_scenarios_use_synthetic_data_only(self):
        forbidden_terms = [
            "@",
            "gmail",
            "real broker",
            "real customer",
            "private",
            "phone",
        ]

        for scenario in DECISION_ENGINE_SCENARIOS:
            with self.subTest(scenario=scenario["scenario_id"]):
                serialized = json.dumps(scenario).lower()
                self.assertIn("synthetic", serialized)
                self.assertIn("synth-de-", serialized)

                for term in forbidden_terms:
                    self.assertNotIn(term, serialized)


if __name__ == "__main__":
    unittest.main()
