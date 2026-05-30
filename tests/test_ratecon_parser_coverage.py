import inspect
import json
import unittest

from app.market_intelligence.intake import ratecon_parser_coverage
from app.market_intelligence.intake.ratecon_parser_coverage import (
    build_ratecon_parser_coverage_report,
)


PRIVATE_LOOKING_VALUE = "PRIVATE VALUE SHOULD NOT APPEAR"


class RateConParserCoverageTests(unittest.TestCase):
    def test_label_detected_but_parser_misses_field_creates_gap(self):
        text = "Motor Carrier Authority: 000000\nRate: 3000"

        report = build_ratecon_parser_coverage_report(text)

        self.assertGreater(report["signal_counts"]["broker_mc"], 0)
        self.assertIn("broker_mc", report["suspected_parser_gap_fields"])
        self.assertEqual(report["extracted_field_status"]["broker_mc"], "missing")
        self.assertEqual(report["result_category"], "PARSER_GAPS_DETECTED")

    def test_extracted_field_is_covered(self):
        text = "Broker MC: 000000\nRate: 3000"

        report = build_ratecon_parser_coverage_report(text)

        self.assertGreater(report["signal_counts"]["broker_mc"], 0)
        self.assertEqual(report["extracted_field_status"]["broker_mc"], "yes")
        self.assertNotIn("broker_mc", report["suspected_parser_gap_fields"])

    def test_zero_numeric_value_counts_as_extracted_for_status_only(self):
        dry_run_result = {
            "parser_output": {
                "rate": 0,
            },
            "intake_summary": {
                "missing_fields": [],
                "needs_check_fields": [],
            },
            "status": "READY_FOR_REVIEW",
        }

        report = build_ratecon_parser_coverage_report(
            "TOTAL: USD $0000.00",
            dry_run_result=dry_run_result,
        )

        self.assertEqual(report["extracted_field_status"]["rate"], "yes")
        self.assertNotIn("rate", report["suspected_parser_gap_fields"])

    def test_missing_labels_are_not_parser_gaps(self):
        text = "Rate: 3000"

        report = build_ratecon_parser_coverage_report(text)

        self.assertEqual(report["signal_counts"]["commodity"], 0)
        self.assertIn("commodity", report["missing_fields"])
        self.assertNotIn("commodity", report["suspected_parser_gap_fields"])

    def test_accepts_existing_dry_run_result_without_values_in_output(self):
        dry_run_result = {
            "parser_output": {
                "broker_name": PRIVATE_LOOKING_VALUE,
                "broker_mc": "",
                "rate": 3000,
                "special_requirements": [],
            },
            "intake_summary": {
                "missing_fields": ["broker_mc"],
                "needs_check_fields": [],
            },
            "status": "MISSING_FIELDS",
        }

        report = build_ratecon_parser_coverage_report(
            "Broker: hidden\nMC#: hidden\nRate: hidden",
            dry_run_result=dry_run_result,
        )
        serialized = json.dumps(report)

        self.assertNotIn(PRIVATE_LOOKING_VALUE, serialized)
        self.assertIn("broker_mc", report["suspected_parser_gap_fields"])

    def test_safe_output_contains_no_raw_text_or_private_values(self):
        text = "Broker: FAKE PRIVATE BROKER\nReference: FAKE-REF-001\nPickup: Fake City"

        report = build_ratecon_parser_coverage_report(text)
        serialized = json.dumps(report)

        self.assertNotIn("FAKE PRIVATE BROKER", serialized)
        self.assertNotIn("FAKE-REF-001", serialized)
        self.assertNotIn("Fake City", serialized)

    def test_output_is_json_serializable(self):
        report = build_ratecon_parser_coverage_report("Rate: 3000")

        json.dumps(report)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(ratecon_parser_coverage).lower()
        forbidden = [
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "pypdf",
            "pytesseract",
            "easyocr",
            "gspread",
            "gmail",
            "smtplib",
            "imaplib",
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
