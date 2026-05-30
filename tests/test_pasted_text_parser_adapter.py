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
from tests.fixtures.anonymized_ratecon_scenarios import (
    ANONYMIZED_RATECON_SCENARIOS,
)


def fixture(scenario_id):
    return next(
        scenario
        for scenario in PASTED_TEXT_RATECON_EXAMPLES
        if scenario["scenario_id"] == scenario_id
    )


def anonymized_fixture(scenario_id):
    return next(
        scenario
        for scenario in ANONYMIZED_RATECON_SCENARIOS
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

    def test_identity_and_main_field_aliases_work(self):
        text = """
Bill To: Synthetic Alias Broker
MC#: MC000000
Total Carrier Pay: USD $3,450
Load #: FAKE-ALIAS-001
Pickup: Fake City, ST
Pickup Date: 2026-10-01
Delivery: Fake Town, ST
Delivery Date: 2026-10-02
Commodity: FAKE PRODUCT
Weight: 40000
Equipment: Conestoga
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["broker_name"], "Synthetic Alias Broker")
        self.assertEqual(parsed["broker_mc"], "MC000000")
        self.assertEqual(parsed["rate"], 3450)
        self.assertEqual(parsed["reference_id"], "FAKE-ALIAS-001")
        self.assertEqual(parsed["field_confidence"]["broker_name"], "MEDIUM")
        self.assertEqual(parsed["field_confidence"]["broker_mc"], "MEDIUM")
        self.assertEqual(parsed["field_confidence"]["rate"], "HIGH")
        self.assertEqual(parsed["field_confidence"]["reference_id"], "MEDIUM")

    def test_total_usd_amount_with_decimal_extracts_rate(self):
        text = """
Broker Name: FAKE BROKER LLC
Broker MC: MC000000
TOTAL: USD $0000.00
Load #: FAKE-SHAPE-001
Pickup: Fake City, ST 00000
Pickup Date: 2026-11-10
Delivery: Fake Town, ST 00000
Delivery Date: 2026-11-11
Commodity: FAKE COMMODITY
Weight: 40000 LBS
Equipment: Conestoga
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["rate"], 0)
        self.assertEqual(parsed["reference_id"], "FAKE-SHAPE-001")
        self.assertEqual(parsed["field_confidence"]["rate"], "HIGH")

    def test_conflicting_reference_aliases_are_marked_low_confidence(self):
        text = """
Broker: Synthetic Conflict Broker
Broker MC: MC000000
Rate: 3000
Load #: FAKE-CONFLICT-001
Reference #: FAKE-CONFLICT-002
Pickup: Fake City, ST
Pickup Date: 2026-10-01
Delivery: Fake Town, ST
Delivery Date: 2026-10-02
Commodity: FAKE PRODUCT
Weight: 40000
Equipment: Flatbed
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["reference_id"], "FAKE-CONFLICT-001")
        self.assertEqual(parsed["field_confidence"]["reference_id"], "LOW")
        self.assertIn("REFERENCE_NEEDS_REVIEW", parsed["special_requirements"])

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

    def test_shipper_and_consignee_blocks_extract_locations_conservatively(self):
        text = """
Broker: Synthetic Block Broker
Broker MC: MC000000
Rate: 3000
Reference #: FAKE-BLOCK-001
Shipper Information:
Name: FAKE SHIPPER LLC
Address: Fake City, ST 00000
Pick Up Time: 2026-10-01 08:00-12:00
Consignee Information:
Name: FAKE CONSIGNEE LLC
Address: Fake Town, ST 00000
Delivery Time: 2026-10-03 09:00-11:00
Commodity: FAKE PRODUCT
Weight: 40000
Equipment: Conestoga
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["pickup_location"], "Fake City, ST 00000")
        self.assertEqual(parsed["delivery_location"], "Fake Town, ST 00000")
        self.assertEqual(parsed["pickup_date"], "2026-10-01")
        self.assertEqual(parsed["pickup_time"], "08:00-12:00")
        self.assertEqual(parsed["delivery_date"], "2026-10-03")
        self.assertEqual(parsed["delivery_time"], "09:00-11:00")
        self.assertEqual(parsed["field_confidence"]["pickup_location"], "MEDIUM")
        self.assertEqual(parsed["field_confidence"]["delivery_location"], "MEDIUM")

    def test_pickup_delivery_time_date_only_values_extract_dates(self):
        text = """
Broker Name: FAKE BROKER LLC
Broker MC: MC000000
Rate: $0000.00
Load #: FAKE-SHAPE-002
Shipper Information:
Address: Fake City, ST 00000
Pick Up Time: 2026-11-12
Consignee Information:
Address: Fake Town, ST 00000
Delivery Time: 2026-11-13
Commodity: FAKE PRODUCT
Total Weight: 40000 LBS
Trailer Type/Size: Flatbed 48
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["pickup_location"], "Fake City, ST 00000")
        self.assertEqual(parsed["delivery_location"], "Fake Town, ST 00000")
        self.assertEqual(parsed["pickup_date"], "2026-11-12")
        self.assertEqual(parsed["pickup_time"], "")
        self.assertEqual(parsed["delivery_date"], "2026-11-13")
        self.assertEqual(parsed["delivery_time"], "")

    def test_pickup_delivery_label_variants_extract_locations(self):
        text = """
Broker: Synthetic Location Broker
Broker MC: MC000000
Rate: 3100
Reference #: FAKE-BLOCK-002
PU: Fake City, ST
Pickup Date: 2026-10-04
Drop: Fake Town, ST
Delivery Date: 2026-10-05
Commodity: FAKE PRODUCT
Weight: 39000
Equipment: Flatbed
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["pickup_location"], "Fake City, ST")
        self.assertEqual(parsed["delivery_location"], "Fake Town, ST")
        self.assertEqual(parsed["field_confidence"]["pickup_location"], "MEDIUM")
        self.assertEqual(parsed["field_confidence"]["delivery_location"], "MEDIUM")

    def test_multi_stop_labels_create_review_signal_without_routing(self):
        text = """
Broker: Synthetic Multi Stop Broker
Broker MC: MC000000
Rate: 4300
Reference #: FAKE-BLOCK-003
PU1: Fake City, ST
PU2: Fake City, ST
Drop 1: Fake Town, ST
Drop 2: Fake Town, ST
Pickup Date: 2026-10-06
Delivery Date: 2026-10-08
Commodity: FAKE PRODUCT
Weight: 41000
Equipment: Flatbed
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["pickup_location"], "")
        self.assertEqual(parsed["delivery_location"], "")
        self.assertIn("MULTI_STOP_NEEDS_REVIEW", parsed["special_requirements"])
        self.assertIn("STOP_DETAILS_NEED_REVIEW", parsed["special_requirements"])
        self.assertEqual(parsed["field_confidence"]["special_requirements"], "LOW")

    def test_special_requirements_extracted_as_list(self):
        self.assert_expected_fields("special_requirements")
        self.assert_expected_fields("conestoga_specific")
        self.assert_expected_fields("flatbed_specific")

    def test_equipment_commodity_and_weight_aliases_extract(self):
        text = """
Broker: Synthetic Freight Broker
Broker MC: MC000000
Rate: 3250
Reference #: FAKE-FREIGHT-001
Pickup: Fake City, ST
Pickup Date: 2026-10-01
Delivery: Fake Town, ST
Delivery Date: 2026-10-02
Freight Description: FAKE PIPE
Pounds: 42,000 LBS
Trailer Type/Size: Conestoga 48
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["commodity"], "FAKE PIPE")
        self.assertEqual(parsed["weight"], 42000)
        self.assertEqual(parsed["equipment"], "Conestoga 48")
        self.assertEqual(parsed["field_confidence"]["commodity"], "MEDIUM")
        self.assertEqual(parsed["field_confidence"]["weight"], "MEDIUM")
        self.assertEqual(parsed["field_confidence"]["equipment"], "HIGH")

    def test_table_like_commodity_weight_equipment_row_extracts(self):
        text = """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Total Carrier Pay: $0000.00
Order #: FAKE-SHAPE-003
Pickup Location: Fake City, ST 00000
Pickup Date: 2026-11-16
Delivery Location: Fake Town, ST 00000
Delivery Date: 2026-11-17
Commodity Description    FAKE TABLE PRODUCT    40000 LBS    Flatbed
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["commodity"], "FAKE TABLE PRODUCT")
        self.assertEqual(parsed["weight"], 40000)
        self.assertEqual(parsed["equipment"], "Flatbed")
        self.assertEqual(parsed["field_confidence"]["commodity"], "MEDIUM")
        self.assertEqual(parsed["field_confidence"]["weight"], "MEDIUM")
        self.assertEqual(parsed["field_confidence"]["equipment"], "MEDIUM")

    def test_next_line_labels_extract_batch3_identity_and_main_fields(self):
        parsed = parse_pasted_text_to_parser_output(
            anonymized_fixture("batch3_next_line_identity_and_rate")["text"]
        )

        self.assertEqual(parsed["broker_name"], "FAKE BROKER LLC")
        self.assertEqual(parsed["broker_mc"], "MC000000")
        self.assertEqual(parsed["rate"], 0)
        self.assertEqual(parsed["reference_id"], "FAKE-REF-024")
        self.assertEqual(parsed["pickup_location"], "Fake City, ST 00000")
        self.assertEqual(parsed["pickup_date"], "2026-11-20")
        self.assertEqual(parsed["delivery_location"], "Fake Town, ST 00000")
        self.assertEqual(parsed["delivery_date"], "2026-11-21")
        self.assertEqual(parsed["commodity"], "FAKE PRODUCT")
        self.assertEqual(parsed["weight"], 40000)
        self.assertEqual(parsed["equipment"], "Flatbed")

    def test_table_like_stop_and_freight_rows_extract_batch3_fields(self):
        parsed = parse_pasted_text_to_parser_output(
            anonymized_fixture("batch3_table_like_stops_and_freight")["text"]
        )

        self.assertEqual(parsed["pickup_location"], "Fake City, ST 00000")
        self.assertEqual(parsed["pickup_date"], "2026-11-22")
        self.assertEqual(parsed["pickup_time"], "08:00")
        self.assertEqual(parsed["delivery_location"], "Fake Town, ST 00000")
        self.assertEqual(parsed["delivery_date"], "2026-11-23")
        self.assertEqual(parsed["delivery_time"], "09:00")
        self.assertEqual(parsed["commodity"], "FAKE COMMODITY")
        self.assertEqual(parsed["weight"], 40000)
        self.assertEqual(parsed["equipment"], "Conestoga")

    def test_authority_and_origin_destination_blocks_extract_conservatively(self):
        parsed = parse_pasted_text_to_parser_output(
            anonymized_fixture("batch3_authority_and_origin_destination_blocks")[
                "text"
            ]
        )

        self.assertEqual(parsed["broker_name"], "FAKE BROKER LLC")
        self.assertEqual(parsed["broker_mc"], "MC000000")
        self.assertEqual(parsed["rate"], 0)
        self.assertEqual(parsed["reference_id"], "FAKE-REF-026")
        self.assertEqual(parsed["pickup_location"], "Fake City, ST 00000")
        self.assertEqual(parsed["pickup_date"], "2026-11-24")
        self.assertEqual(parsed["delivery_location"], "Fake Town, ST 00000")
        self.assertEqual(parsed["delivery_date"], "2026-11-25")
        self.assertEqual(parsed["commodity"], "FAKE PRODUCT")
        self.assertEqual(parsed["weight"], 40000)
        self.assertEqual(parsed["equipment"], "Step Deck")
        self.assertEqual(parsed["field_confidence"]["broker_mc"], "LOW")

    def test_next_line_accessorial_total_extracts_total_and_review_context(self):
        parsed = parse_pasted_text_to_parser_output(
            anonymized_fixture("batch3_accessorial_total_next_line")["text"]
        )

        self.assertEqual(parsed["rate"], 0)
        self.assertIn("ACCESSORIALS_PRESENT", parsed["special_requirements"])
        self.assertEqual(parsed["field_confidence"]["rate"], "HIGH")

    def test_tbd_commodity_and_weight_stay_missing_with_review_signal(self):
        text = """
Broker: Synthetic TBD Broker
Broker MC: MC000000
Rate: 3000
Reference #: FAKE-FREIGHT-002
Pickup: Fake City, ST
Pickup Date: 2026-10-03
Delivery: Fake Town, ST
Delivery Date: 2026-10-04
Product: TBD
Total Weight: call for weight
Equipment: Flatbed
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["commodity"], "")
        self.assertEqual(parsed["weight"], "")
        self.assertIn("COMMODITY_NEEDS_REVIEW", parsed["special_requirements"])
        self.assertIn("WEIGHT_NEEDS_REVIEW", parsed["special_requirements"])
        self.assertEqual(parsed["field_confidence"]["commodity"], "LOW")
        self.assertEqual(parsed["field_confidence"]["weight"], "LOW")

    def test_generic_mode_does_not_override_specific_equipment(self):
        text = """
Broker: Synthetic Equipment Broker
Broker MC: MC000000
Rate: 3100
Reference #: FAKE-FREIGHT-003
Pickup: Fake City, ST
Pickup Date: 2026-10-05
Delivery: Fake Town, ST
Delivery Date: 2026-10-06
Commodity Description: FAKE STEEL
Weight: 40000
Mode: Truckload
Equipment: Step Deck
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["equipment"], "Step Deck")
        self.assertIn("EQUIPMENT_NEEDS_REVIEW", parsed["special_requirements"])
        self.assertEqual(parsed["field_confidence"]["equipment"], "HIGH")

    def test_multiple_rates_handled_conservatively(self):
        self.assert_expected_fields("multiple_rates_accessorials")
        parsed = parse_pasted_text_to_parser_output(
            fixture("multiple_rates_accessorials")["pasted_text"]
        )

        self.assertEqual(parsed["rate"], "")
        self.assertIn("ACCESSORIALS_PRESENT", parsed["special_requirements"])
        self.assertEqual(parsed["field_confidence"]["rate"], "UNKNOWN")

    def test_total_carrier_pay_with_accessorials_extracts_clear_total_only(self):
        text = """
Broker: Synthetic Accessorial Broker
Broker MC: MC000000
Linehaul: 2500
Fuel Surcharge: 300
Detention: FAKE TERMS
Total Carrier Pay: 2800
Reference #: FAKE-RATE-001
Pickup: Fake City, ST
Pickup Date: 2026-10-01
Delivery: Fake Town, ST
Delivery Date: 2026-10-02
Commodity: FAKE PRODUCT
Weight: 40000
Equipment: Flatbed
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["rate"], 2800)
        self.assertEqual(parsed["field_confidence"]["rate"], "HIGH")
        self.assertIn("ACCESSORIALS_PRESENT", parsed["special_requirements"])

    def test_accessorial_amounts_without_total_do_not_set_rate(self):
        text = """
Broker: Synthetic Accessorial Broker
Broker MC: MC000000
Linehaul: 2500
Fuel Surcharge: 300
Layover Fee: 100
Lumper Fee: 50
TONU Fee: 150
Reference #: FAKE-RATE-002
Pickup: Fake City, ST
Pickup Date: 2026-10-03
Delivery: Fake Town, ST
Delivery Date: 2026-10-04
Commodity: FAKE PRODUCT
Weight: 40000
Equipment: Van
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["rate"], "")
        self.assertEqual(parsed["field_confidence"]["rate"], "UNKNOWN")
        self.assertEqual(
            parsed["special_requirements"].count("ACCESSORIALS_PRESENT"),
            1,
        )

    def test_conflicting_rate_totals_are_review_only(self):
        text = """
Broker: Synthetic Rate Conflict Broker
Broker MC: MC000000
Rate: 3000
Total Rate: 3250
Reference #: FAKE-RATE-003
Pickup: Fake City, ST
Pickup Date: 2026-10-05
Delivery: Fake Town, ST
Delivery Date: 2026-10-06
Commodity: FAKE PRODUCT
Weight: 40000
Equipment: Conestoga
"""
        parsed = parse_pasted_text_to_parser_output(text)

        self.assertEqual(parsed["rate"], "")
        self.assertEqual(parsed["field_confidence"]["rate"], "LOW")
        self.assertIn("RATE_NEEDS_REVIEW", parsed["special_requirements"])

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
