import copy
import inspect
import json
import unittest

from app.market_intelligence.intake import pasted_text_parser_adapter
from app.market_intelligence.intake.parser_contract import normalize_parser_output
from app.market_intelligence.intake.pasted_text_parser_adapter import (
    parse_pasted_text_to_parser_output,
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


class PastedTextParserAdapterTests(unittest.TestCase):
    def assert_expected_fields(self, scenario_id):
        scenario = fixture(scenario_id)
        parsed = parse_pasted_text_to_parser_output(scenario["pasted_text"])
        expected = scenario["expected_parser_output"]

        for field_name, expected_value in expected.items():
            if field_name == "field_confidence":
                continue

            with self.subTest(scenario=scenario_id, field=field_name):
                self.assertEqual(parsed.get(field_name), expected_value)

        for field_name, expected_confidence in scenario["expected_confidence"].items():
            with self.subTest(scenario=scenario_id, confidence=field_name):
                self.assertEqual(
                    parsed["field_confidence"].get(field_name),
                    expected_confidence,
                )

    def test_clean_pasted_text_extracts_expected_fields(self):
        self.assert_expected_fields("clean_simple_ratecon_text")

    def test_missing_fields_remain_blank(self):
        self.assert_expected_fields("missing_broker_mc")
        self.assert_expected_fields("missing_weight")
        self.assert_expected_fields("missing_commodity")

    def test_broker_mc_label_variants_work(self):
        text = """
Broker Name: Synthetic Variant Broker
MC Number: SYNTH-MC-9201
Rate: 3000
Pickup: Dallas, TX
Pickup Date: 2026-08-01
Delivery: Denver, CO
Delivery Date: 2026-08-02
Commodity: Synthetic steel
Weight: 40000
Reference: SYNTH-VARIANT-001
Equipment: Conestoga
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["broker_name"], "Synthetic Variant Broker")
        self.assertEqual(parsed["broker_mc"], "SYNTH-MC-9201")
        self.assertEqual(parsed["field_confidence"]["broker_mc"], "MEDIUM")

    def test_reference_label_variants_work(self):
        self.assert_expected_fields("appointment_window")
        self.assert_expected_fields("unusual_reference_label")

    def test_date_and_time_labels_extract_safely(self):
        parsed = parse_pasted_text_to_parser_output(
            fixture("appointment_window")["pasted_text"]
        )

        self.assertEqual(parsed["pickup_date"], "2026-07-12")
        self.assertEqual(parsed["pickup_time"], "08:00-12:00")
        self.assertEqual(parsed["delivery_date"], "2026-07-14")
        self.assertEqual(parsed["delivery_time"], "09:00-15:00")
        self.assertEqual(parsed["field_confidence"]["pickup_time"], "MEDIUM")
        self.assertEqual(parsed["field_confidence"]["delivery_time"], "MEDIUM")

    def test_special_requirements_extracted_as_list(self):
        self.assert_expected_fields("special_requirements")
        self.assert_expected_fields("conestoga_specific")
        self.assert_expected_fields("flatbed_specific")

    def test_multiple_rates_handled_conservatively(self):
        self.assert_expected_fields("multiple_rates_accessorials")
        parsed = parse_pasted_text_to_parser_output(
            fixture("multiple_rates_accessorials")["pasted_text"]
        )

        self.assertEqual(parsed["rate"], "")
        self.assertIn("ACCESSORIALS_PRESENT", parsed["special_requirements"])
        self.assertEqual(parsed["field_confidence"]["rate"], "UNKNOWN")

    def test_ambiguous_broker_context_stays_conservative(self):
        self.assert_expected_fields("ambiguous_broker_contact_heavy")

    def test_multi_stop_like_text_stays_review_context_only(self):
        self.assert_expected_fields("multi_stop_like_text")

    def test_output_normalizes_through_parser_contract(self):
        for scenario in PASTED_TEXT_RATECON_EXAMPLES:
            with self.subTest(scenario=scenario["scenario_id"]):
                parsed = parse_pasted_text_to_parser_output(scenario["pasted_text"])
                record = normalize_parser_output(parsed)

                self.assertEqual(
                    record["missing_fields"],
                    scenario["expected_missing_fields"],
                )
                self.assertEqual(
                    record["needs_check_fields"],
                    scenario["expected_needs_check_fields"],
                )

    def test_field_confidence_exists_and_is_json_safe(self):
        parsed = parse_pasted_text_to_parser_output(
            fixture("clean_simple_ratecon_text")["pasted_text"]
        )

        self.assertIsInstance(parsed["field_confidence"], dict)
        json.dumps(parsed)

    def test_helper_does_not_mutate_inputs(self):
        scenario = copy.deepcopy(fixture("clean_simple_ratecon_text"))
        before = copy.deepcopy(scenario)

        parse_pasted_text_to_parser_output(scenario["pasted_text"])

        self.assertEqual(scenario, before)

    def test_empty_text_returns_safe_output(self):
        parsed = parse_pasted_text_to_parser_output("")
        record = normalize_parser_output(parsed)

        self.assertEqual(parsed["source_type"], "manual_pasted_text")
        self.assertEqual(parsed["special_requirements"], [])
        self.assertIn("broker_name", parsed["field_confidence"])
        self.assertIn("rate", parsed["field_confidence"])
        self.assertIn("broker_name", record["missing_fields"])

    def test_helper_has_no_forbidden_imports(self):
        source = inspect.getsource(pasted_text_parser_adapter).lower()
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
