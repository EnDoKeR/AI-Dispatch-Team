import copy
import inspect
import json
import unittest

from app.market_intelligence.decision_engine import scenario_runner
from app.market_intelligence.decision_engine.scenario_runner import (
    run_decision_engine_scenarios,
    validate_scenario,
)
from tests.fixtures.decision_engine_scenarios import DECISION_ENGINE_SCENARIOS


class DecisionEngineScenarioRunnerTest(unittest.TestCase):
    def test_runner_processes_all_scenarios(self):
        report = run_decision_engine_scenarios(DECISION_ENGINE_SCENARIOS)

        self.assertTrue(report["dry_run"])
        self.assertEqual(report["total"], len(DECISION_ENGINE_SCENARIOS))
        self.assertEqual(report["passed"], len(DECISION_ENGINE_SCENARIOS))
        self.assertEqual(report["failed"], 0)
        self.assertEqual(len(report["scenario_results"]), len(DECISION_ENGINE_SCENARIOS))

    def test_clean_scenario_passes(self):
        scenario = next(
            item
            for item in DECISION_ENGINE_SCENARIOS
            if item["scenario_id"] == "clean_match_good_rate"
        )

        result = validate_scenario(scenario)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["decision"], "MATCH")
        self.assertEqual(result["risk_flags"], [])
        self.assertTrue(result["approval_required"])

    def test_missing_and_risk_scenarios_pass(self):
        report = run_decision_engine_scenarios(DECISION_ENGINE_SCENARIOS)

        self.assertEqual(report["decision_summary"]["REVIEW_ONCE"], 10)
        self.assertEqual(report["decision_summary"]["BLOCK"], 1)
        self.assertEqual(report["decision_summary"]["MATCH"], 1)
        self.assertEqual(report["risk_flag_summary"]["MISSING_RATE"], 1)
        self.assertEqual(report["risk_flag_summary"]["NO_CONESTOGA"], 1)
        self.assertEqual(report["risk_flag_summary"]["WEAK_EXIT_MARKET"], 1)

    def test_unknown_risk_flag_fails_clearly(self):
        scenario = copy.deepcopy(DECISION_ENGINE_SCENARIOS[0])
        scenario["scenario_id"] = "unknown_flag_example"
        scenario["expected_risk_flags"] = ["FUTURE_UNKNOWN_FLAG"]

        result = validate_scenario(scenario)

        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["issues"], ["Unknown risk flags: FUTURE_UNKNOWN_FLAG"])

    def test_report_is_json_serializable(self):
        report = run_decision_engine_scenarios(DECISION_ENGINE_SCENARIOS)
        json.dumps(report)

    def test_runner_does_not_mutate_scenarios(self):
        scenarios = copy.deepcopy(DECISION_ENGINE_SCENARIOS)
        before = copy.deepcopy(scenarios)

        run_decision_engine_scenarios(scenarios)

        self.assertEqual(scenarios, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(scenario_runner).lower()

        forbidden_terms = [
            "telegram",
            "dispatch_case",
            "market_models",
            "marketload",
            "case_event_builder",
            "event_logger",
            "pypdf",
            "gspread",
            "googlemaps",
            "dat_api",
            "apscheduler",
            "threading",
            "sqlite",
            "jsonl",
            "open(",
            "write_text(",
            "read_text(",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
