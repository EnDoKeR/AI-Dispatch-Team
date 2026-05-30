import copy
import inspect
import json
import unittest

from app.market_intelligence.intake import ratecon_text_dry_run
from app.market_intelligence.intake.ratecon_text_dry_run import (
    run_ratecon_text_dry_run,
)


CLEAN_TEXT = """
Broker: Synthetic Manual Broker
Broker MC: 000123
Load: FAKE LOAD
Rate: 3400
Pickup: Dallas, TX
Pickup Date: 2026-09-01
Pickup Time: 08:00
Delivery: Denver, CO
Delivery Date: 2026-09-03
Delivery Time: 09:00
Commodity: Synthetic steel
Weight: 40000
Reference: SYN-MANUAL-001
Equipment: Conestoga
Special Requirements: APPOINTMENT_REQUIRED
""".strip()


MATCHING_CASE = {
    "case_id": "CASE-MANUAL-001",
    "reference_id": "SYN-MANUAL-001",
    "broker_name": "Synthetic Manual Broker",
    "broker_mc": "000123",
    "pickup": "Dallas, TX",
    "delivery": "Denver, CO",
    "rate": 3400,
}


class RateConTextDryRunTests(unittest.TestCase):
    def test_sample_clean_text_produces_parser_output_and_intake_record(self):
        result = run_ratecon_text_dry_run(CLEAN_TEXT, intake_id="INTAKE-MANUAL-1")

        self.assertTrue(result["dry_run_only"])
        self.assertFalse(result["private_text_saved"])
        self.assertEqual(result["parser_output"]["broker_name"], "Synthetic Manual Broker")
        self.assertEqual(result["intake_record"]["intake_id"], "INTAKE-MANUAL-1")
        self.assertEqual(result["intake_record"]["reference_id"], "SYN-MANUAL-001")
        self.assertEqual(result["status"], "READY_FOR_REVIEW")

    def test_missing_fields_appear_in_intake_summary(self):
        result = run_ratecon_text_dry_run("Broker: Synthetic Missing Fields")

        missing_fields = result["intake_summary"]["missing_fields"]

        self.assertIn("broker_mc", missing_fields)
        self.assertIn("rate", missing_fields)
        self.assertIn("pickup_location", missing_fields)
        self.assertEqual(result["status"], "MISSING_FIELDS")

    def test_missing_optional_broker_mc_and_equipment_do_not_fail_core_policy(self):
        text = """
Broker: Synthetic Core Broker
Load: FAKE LOAD
Rate: 3400
Pickup: Dallas, TX
Pickup Date: 2026-09-01
Delivery: Denver, CO
Delivery Date: 2026-09-03
Commodity: Synthetic steel
Weight: 40000
Reference: SYN-MANUAL-CORE
""".strip()
        result = run_ratecon_text_dry_run(text)

        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertEqual(result["missing_core_fields"], [])
        self.assertIn("broker_mc", result["optional_missing_fields"])
        self.assertIn("equipment", result["optional_missing_fields"])
        self.assertIn("loaded_miles", result["deferred_fields"])
        self.assertEqual(result["miles_status"], "DEFERRED_GOOGLE_MAPS")
        self.assertEqual(result["miles_source"], "NOT_FROM_RATECON")

    def test_low_confidence_appears_in_warnings(self):
        text = (
            "Company Header: Synthetic Contact Heavy Header\n"
            "Rate: 3000\n"
        )

        result = run_ratecon_text_dry_run(text)

        self.assertIn("low_confidence_broker_name", result["warnings"])

    def test_with_case_record_produces_link_candidate(self):
        result = run_ratecon_text_dry_run(CLEAN_TEXT, case_record=MATCHING_CASE)
        candidate = result["link_candidate"]

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["recommended_action"], "LINK_EXISTING")
        self.assertTrue(candidate["approval_required"])
        self.assertFalse(result["cases_created"])
        self.assertFalse(result["events_written"])

    def test_without_case_record_does_not_create_or_link_case(self):
        result = run_ratecon_text_dry_run(CLEAN_TEXT)

        self.assertIsNone(result["link_candidate"])
        self.assertEqual(result["intake_record"]["linked_dispatch_case_id"], "")
        self.assertFalse(result["cases_created"])
        self.assertFalse(result["events_written"])

    def test_empty_text_is_safe(self):
        result = run_ratecon_text_dry_run("")

        self.assertEqual(result["status"], "MISSING_FIELDS")
        self.assertIn("empty_text", result["warnings"])
        self.assertEqual(result["parser_output"]["source_type"], "manual_pasted_text")

    def test_output_is_json_serializable(self):
        result = run_ratecon_text_dry_run(CLEAN_TEXT, case_record=MATCHING_CASE)

        json.dumps(result)

    def test_helper_does_not_mutate_inputs(self):
        case_record = copy.deepcopy(MATCHING_CASE)
        case_before = copy.deepcopy(case_record)

        run_ratecon_text_dry_run(CLEAN_TEXT, case_record=case_record)

        self.assertEqual(case_record, case_before)

    def test_helper_has_no_forbidden_imports(self):
        source = inspect.getsource(ratecon_text_dry_run)

        forbidden = [
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "telegram_sender",
            "telegram_notifier",
            "pypdf",
            "pytesseract",
            "gspread",
            "google.oauth",
            "googlemaps",
            "dat_api",
            "load_intake",
            "open(",
            "write_text",
            "read_text",
            "read_bytes",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
