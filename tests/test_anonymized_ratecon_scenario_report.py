import copy
import inspect
import json
import unittest

from app.market_intelligence.intake import anonymized_ratecon_scenario_report
from app.market_intelligence.intake.anonymized_ratecon_scenario_report import (
    build_anonymized_ratecon_scenario_report,
)
from tests.fixtures.anonymized_ratecon_scenarios import (
    ANONYMIZED_RATECON_SCENARIOS,
)


class AnonymizedRateConScenarioReportTests(unittest.TestCase):
    def test_empty_report_safe(self):
        report = build_anonymized_ratecon_scenario_report([])

        self.assertEqual(report["total_scenarios"], 0)
        self.assertEqual(report["fields_expected"], {})
        self.assertEqual(report["scenario_results"], [])

    def test_report_processes_all_synthetic_fixtures(self):
        report = build_anonymized_ratecon_scenario_report(
            ANONYMIZED_RATECON_SCENARIOS
        )

        self.assertEqual(
            report["total_scenarios"],
            len(ANONYMIZED_RATECON_SCENARIOS),
        )
        self.assertEqual(len(report["scenario_results"]), len(ANONYMIZED_RATECON_SCENARIOS))

    def test_report_detects_parser_gaps(self):
        report = build_anonymized_ratecon_scenario_report(
            ANONYMIZED_RATECON_SCENARIOS
        )

        self.assertTrue(report["suspected_parser_gap_fields"])
        self.assertIn("rate", report["suspected_parser_gap_fields"])

    def test_report_counts_gap_fields(self):
        report = build_anonymized_ratecon_scenario_report(
            ANONYMIZED_RATECON_SCENARIOS
        )

        self.assertEqual(
            report["counts_by_gap_field"],
            report["suspected_parser_gap_fields"],
        )
        self.assertGreater(report["counts_by_gap_field"].get("pickup_location", 0), 0)

    def test_identity_main_field_aliases_reduce_gaps_for_clean_header(self):
        scenario = next(
            item
            for item in ANONYMIZED_RATECON_SCENARIOS
            if item["scenario_id"] == "truckload_rate_confirmation_header"
        )
        report = build_anonymized_ratecon_scenario_report([scenario])
        result = report["scenario_results"][0]

        self.assertNotIn("broker_name", result["suspected_parser_gap_fields"])
        self.assertNotIn("broker_mc", result["suspected_parser_gap_fields"])
        self.assertNotIn("rate", result["suspected_parser_gap_fields"])
        self.assertNotIn("reference_id", result["suspected_parser_gap_fields"])

    def test_report_contains_no_raw_scenario_text_or_values(self):
        report = build_anonymized_ratecon_scenario_report(
            ANONYMIZED_RATECON_SCENARIOS
        )
        serialized = json.dumps(report)

        self.assertNotIn("FAKE BROKER LLC", serialized)
        self.assertNotIn("FAKE-REF-", serialized)
        self.assertNotIn("Fake City", serialized)
        self.assertNotIn("Fake Town", serialized)

    def test_report_is_json_serializable(self):
        report = build_anonymized_ratecon_scenario_report(
            ANONYMIZED_RATECON_SCENARIOS
        )

        json.dumps(report)

    def test_report_does_not_mutate_inputs(self):
        scenarios = copy.deepcopy(ANONYMIZED_RATECON_SCENARIOS)
        before = copy.deepcopy(scenarios)

        build_anonymized_ratecon_scenario_report(scenarios)

        self.assertEqual(scenarios, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(anonymized_ratecon_scenario_report).lower()
        forbidden = [
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "pypdf",
            "pdfplumber",
            "fitz",
            "pytesseract",
            "easyocr",
            "gspread",
            "google.oauth",
            "gmail",
            "googlemaps",
            "dat_api",
            "load_intake",
            "open(",
            "read_text",
            "read_bytes",
            "write_text",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
