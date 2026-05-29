import inspect
import json
import unittest

from app.market_intelligence.intake import parser_scenario_runner
from app.market_intelligence.intake.parser_scenario_runner import (
    build_parser_scenario_report,
    build_parser_scenario_result,
)
from tests.fixtures.parser_expected_outputs import PARSER_EXPECTED_OUTPUTS


class ParserScenarioRunnerTests(unittest.TestCase):
    def test_runner_processes_all_synthetic_parser_scenarios(self):
        report = build_parser_scenario_report(PARSER_EXPECTED_OUTPUTS)

        self.assertEqual(report["total_scenarios"], len(PARSER_EXPECTED_OUTPUTS))
        self.assertEqual(report["passed"], len(PARSER_EXPECTED_OUTPUTS))
        self.assertEqual(report["failed"], 0)

    def test_clean_scenario_passes(self):
        scenario = next(
            item
            for item in PARSER_EXPECTED_OUTPUTS
            if item["scenario_id"] == "clean_ratecon_parser_output"
        )
        result = build_parser_scenario_result(scenario)

        self.assertTrue(result["passed"])
        self.assertEqual(result["missing_fields"], [])
        self.assertEqual(result["needs_check_fields"], [])

    def test_missing_broker_mc_scenario_matches_expected(self):
        scenario = next(
            item
            for item in PARSER_EXPECTED_OUTPUTS
            if item["scenario_id"] == "missing_broker_mc"
        )
        result = build_parser_scenario_result(scenario)

        self.assertTrue(result["passed"])
        self.assertEqual(result["missing_fields"], ["broker_mc"])
        self.assertEqual(result["needs_check_fields"], ["broker_mc"])

    def test_failed_expectation_is_reported(self):
        scenario = dict(PARSER_EXPECTED_OUTPUTS[0])
        scenario["expected_missing_fields"] = ["broker_mc"]
        result = build_parser_scenario_result(scenario)

        self.assertFalse(result["passed"])
        self.assertEqual(result["expected_missing_fields"], ["broker_mc"])
        self.assertEqual(result["missing_fields"], [])

    def test_confidence_expectations_are_checked(self):
        scenario = next(
            item
            for item in PARSER_EXPECTED_OUTPUTS
            if item["scenario_id"] == "low_confidence_fields"
        )
        result = build_parser_scenario_result(scenario)

        self.assertTrue(result["passed"])
        self.assertEqual(
            result["confidence_keys"],
            ["delivery_time", "pickup_time", "weight"],
        )
        self.assertEqual(
            result["field_confidence"],
            {
                "pickup_time": "LOW",
                "delivery_time": "LOW",
                "weight": "LOW",
            },
        )

    def test_summary_counts_are_returned(self):
        report = build_parser_scenario_report(PARSER_EXPECTED_OUTPUTS)

        self.assertEqual(report["missing_field_summary"]["broker_mc"], 1)
        self.assertEqual(report["missing_field_summary"]["commodity"], 1)
        self.assertEqual(report["missing_field_summary"]["weight"], 1)
        self.assertEqual(report["needs_check_summary"]["broker_mc"], 1)
        self.assertGreater(report["confidence_summary"]["HIGH"], 0)
        self.assertGreater(report["confidence_summary"]["LOW"], 0)
        self.assertGreater(report["confidence_summary"]["UNKNOWN"], 0)

    def test_report_is_json_serializable(self):
        report = build_parser_scenario_report(PARSER_EXPECTED_OUTPUTS)

        json.dumps(report)

    def test_scenarios_use_synthetic_data_only(self):
        report = build_parser_scenario_report(PARSER_EXPECTED_OUTPUTS)
        serialized = json.dumps(PARSER_EXPECTED_OUTPUTS).lower()

        self.assertIn("synthetic", serialized)
        self.assertEqual(report["failed"], 0)

        for forbidden in ["@", "phone", "driver", "customer", "real broker", "gmail"]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, serialized)

    def test_runner_has_no_forbidden_imports_or_file_io(self):
        source = inspect.getsource(parser_scenario_runner).lower()

        forbidden = [
            "pypdf",
            "pdfreader",
            "pytesseract",
            "gspread",
            "google.oauth",
            "gmail",
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "event_logger",
            "scheduler",
            "threading",
            "googlemaps",
            "dat_api",
            "app.load_intake",
            "open(",
            "read_text(",
            "read_bytes(",
            "write_text(",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
