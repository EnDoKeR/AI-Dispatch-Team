import copy
import json
import unittest

from app.market_intelligence.decision_engine.combined_report import (
    build_decision_timeline_comparison,
    build_decision_timeline_comparison_report,
)
from tests.fixtures.decision_engine_combined_report_loads import (
    DECISION_ENGINE_COMBINED_REPORT_LOADS,
)


class DecisionEngineCombinedReportLoadsTest(unittest.TestCase):
    def test_fixtures_import(self):
        self.assertEqual(len(DECISION_ENGINE_COMBINED_REPORT_LOADS), 8)

    def test_every_fixture_builds_combined_report_item(self):
        for scenario in DECISION_ENGINE_COMBINED_REPORT_LOADS:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                item = build_decision_timeline_comparison(scenario["load"])

                self.assertEqual(item["load_id"], scenario["load"]["load_id"])

    def test_expected_decision_appears_in_decision_result(self):
        for scenario in DECISION_ENGINE_COMBINED_REPORT_LOADS:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                item = build_decision_timeline_comparison(scenario["load"])

                self.assertEqual(
                    item["decision_result"]["decision"],
                    scenario["expected_decision"],
                )
                self.assertEqual(
                    item["decision_result"]["category"],
                    scenario["expected_category"],
                )

    def test_expected_risk_flags_appear_in_decision_result(self):
        for scenario in DECISION_ENGINE_COMBINED_REPORT_LOADS:
            expected_flags = scenario.get("expected_risk_flags", [])

            with self.subTest(scenario_id=scenario["scenario_id"]):
                item = build_decision_timeline_comparison(scenario["load"])

                for flag in expected_flags:
                    self.assertIn(flag, item["decision_result"]["risk_flags"])

    def test_expected_warnings_appear(self):
        for scenario in DECISION_ENGINE_COMBINED_REPORT_LOADS:
            expected_warnings = scenario.get("expected_warnings", [])

            with self.subTest(scenario_id=scenario["scenario_id"]):
                item = build_decision_timeline_comparison(scenario["load"])

                for warning in expected_warnings:
                    self.assertIn(warning, item["warnings"])

    def test_timeline_preview_event_type_is_ai_decision_created(self):
        for scenario in DECISION_ENGINE_COMBINED_REPORT_LOADS:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                item = build_decision_timeline_comparison(scenario["load"])

                self.assertEqual(
                    item["timeline_preview_payload"]["event_type"],
                    "AI_DECISION_CREATED",
                )

    def test_normalized_event_view_exists(self):
        for scenario in DECISION_ENGINE_COMBINED_REPORT_LOADS:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                item = build_decision_timeline_comparison(scenario["load"])

                self.assertIn("legacy_payload", item["normalized_event_view"])
                self.assertIn("normalized_payload", item["normalized_event_view"])
                self.assertIn("warnings", item["normalized_event_view"])

    def test_fixture_report_is_json_serializable(self):
        report = build_decision_timeline_comparison_report([
            copy.deepcopy(scenario["load"])
            for scenario in DECISION_ENGINE_COMBINED_REPORT_LOADS
        ])

        json.dumps(report)

    def test_no_real_private_data(self):
        fixture_text = json.dumps(DECISION_ENGINE_COMBINED_REPORT_LOADS).lower()

        blocked_terms = [
            "@",
            "gmail",
            "yahoo",
            "outlook",
            "private_ratecons",
            "real broker",
            "real customer",
        ]

        for term in blocked_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, fixture_text)


if __name__ == "__main__":
    unittest.main()
