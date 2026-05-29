import inspect
import json
import unittest

from app.market_intelligence.intake import pasted_text_scenario_runner
from app.market_intelligence.intake.pasted_text_scenario_runner import (
    build_pasted_text_scenario_report,
    build_pasted_text_scenario_result,
)
from tests.fixtures.pasted_text_ratecon_examples import (
    PASTED_TEXT_RATECON_EXAMPLES,
)


def fixture(scenario_id):
    return next(
        scenario
        for scenario in PASTED_TEXT_RATECON_EXAMPLES
        if scenario["scenario_id"] == scenario_id
    )


class PastedTextScenarioRunnerTests(unittest.TestCase):
    def test_all_synthetic_pasted_text_scenarios_process(self):
        report = build_pasted_text_scenario_report(PASTED_TEXT_RATECON_EXAMPLES)

        self.assertEqual(report["total_scenarios"], len(PASTED_TEXT_RATECON_EXAMPLES))
        self.assertEqual(report["passed"], len(PASTED_TEXT_RATECON_EXAMPLES))
        self.assertEqual(report["failed"], 0)

    def test_clean_scenario_passes(self):
        result = build_pasted_text_scenario_result(
            fixture("clean_simple_ratecon_text")
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertEqual(result["missing_fields"], [])
        self.assertEqual(result["needs_check_fields"], [])

    def test_missing_field_scenarios_pass(self):
        for scenario_id, missing_fields in [
            ("missing_broker_mc", ["broker_mc"]),
            ("missing_weight", ["weight"]),
            ("missing_commodity", ["commodity"]),
        ]:
            with self.subTest(scenario=scenario_id):
                result = build_pasted_text_scenario_result(fixture(scenario_id))

                self.assertTrue(result["passed"])
                self.assertEqual(result["missing_fields"], missing_fields)

    def test_ambiguous_multiple_rate_scenario_stays_conservative(self):
        result = build_pasted_text_scenario_result(
            fixture("multiple_rates_accessorials")
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["status"], "MISSING_FIELDS")
        self.assertEqual(result["missing_fields"], ["rate"])
        self.assertIn("RATE_NEEDS_REVIEW", result["special_requirements"])
        self.assertIn("RATE_NEEDS_REVIEW", result["parser_warnings"])

    def test_confidence_expectations_are_checked(self):
        result = build_pasted_text_scenario_result(fixture("appointment_window"))

        self.assertTrue(result["passed"])
        self.assertEqual(result["field_confidence"]["pickup_time"], "MEDIUM")
        self.assertEqual(result["field_confidence"]["delivery_time"], "MEDIUM")

    def test_summary_counts_are_returned(self):
        report = build_pasted_text_scenario_report(PASTED_TEXT_RATECON_EXAMPLES)

        self.assertEqual(report["missing_field_summary"]["broker_mc"], 2)
        self.assertEqual(report["missing_field_summary"]["rate"], 1)
        self.assertEqual(report["missing_field_summary"]["weight"], 1)
        self.assertEqual(report["missing_field_summary"]["commodity"], 1)
        self.assertEqual(report["needs_check_summary"]["broker_mc"], 1)
        self.assertGreater(report["confidence_summary"]["HIGH"], 0)
        self.assertGreater(report["confidence_summary"]["MEDIUM"], 0)
        self.assertGreater(report["confidence_summary"]["UNKNOWN"], 0)
        self.assertEqual(report["parser_warning_summary"]["RATE_NEEDS_REVIEW"], 1)

    def test_report_is_json_serializable(self):
        report = build_pasted_text_scenario_report(PASTED_TEXT_RATECON_EXAMPLES)

        json.dumps(report)

    def test_runner_has_no_forbidden_imports(self):
        source = inspect.getsource(pasted_text_scenario_runner).lower()
        forbidden = [
            "pypdf",
            "pdfreader",
            "pytesseract",
            "ocr",
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
