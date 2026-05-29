import json
import unittest

from app.market_intelligence.decision_engine.comparison_report import (
    build_decision_comparison,
    build_decision_comparison_report,
)
from app.market_intelligence.decision_engine.marketload_adapter import (
    decision_result_from_market_load,
)
from tests.fixtures.decision_engine_comparison_loads import (
    DECISION_ENGINE_COMPARISON_LOADS,
)


class DecisionEngineComparisonFixturesTest(unittest.TestCase):
    def test_fixtures_import_and_are_not_empty(self):
        self.assertGreaterEqual(len(DECISION_ENGINE_COMPARISON_LOADS), 6)

    def test_every_fixture_can_be_adapted(self):
        for fixture in DECISION_ENGINE_COMPARISON_LOADS:
            with self.subTest(fixture=fixture["scenario_id"]):
                result = decision_result_from_market_load(fixture["load"])

                self.assertEqual(result["decision"], fixture["expected_decision"])
                self.assertEqual(result["category"], fixture["expected_category"])

                for flag in fixture["expected_risk_flags"]:
                    self.assertIn(flag, result["risk_flags"])

    def test_comparison_report_processes_all_fixtures(self):
        report = build_decision_comparison_report(
            fixture["load"]
            for fixture in DECISION_ENGINE_COMPARISON_LOADS
        )

        self.assertEqual(report["total"], len(DECISION_ENGINE_COMPARISON_LOADS))
        self.assertEqual(report["decision_mismatch_count"], 0)
        self.assertEqual(report["category_mismatch_count"], 0)
        self.assertIn("RATE_MISSING", report["risk_flag_summary"])
        self.assertIn("TRACKING_REQUIRED", report["risk_flag_summary"])

    def test_expected_matches_and_warnings_are_correct(self):
        for fixture in DECISION_ENGINE_COMPARISON_LOADS:
            with self.subTest(fixture=fixture["scenario_id"]):
                comparison = build_decision_comparison(fixture["load"])

                self.assertEqual(
                    comparison["decision_matches"],
                    fixture["expected_decision_matches"],
                )
                self.assertEqual(
                    comparison["category_matches"],
                    fixture["expected_category_matches"],
                )

                for warning in fixture.get("expected_warnings", []):
                    self.assertIn(warning, comparison["warnings"])

    def test_fixtures_are_json_serializable(self):
        json.dumps(DECISION_ENGINE_COMPARISON_LOADS)

    def test_fixtures_contain_only_synthetic_data(self):
        serialized = json.dumps(DECISION_ENGINE_COMPARISON_LOADS).lower()

        real_data_terms = [
            "@",
            "gmail",
            "yahoo",
            "hotmail",
            "555-",
            "mc#",
            "real broker",
            "real customer",
            "private",
        ]

        for term in real_data_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, serialized)


if __name__ == "__main__":
    unittest.main()
