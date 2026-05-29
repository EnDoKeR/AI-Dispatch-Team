import copy
import inspect
import json
import unittest

from app.market_intelligence import intake_parser_contract
from app.market_intelligence.intake_parser_contract import normalize_parser_output


class FakeParserOutput:
    source_type = "parser_object"
    source_file_name = "synthetic_parser_output.txt"
    broker_name = "Synthetic Parser Broker"
    broker_mc = "SYNTH-MC-2001"
    rate = 3300
    pickup_location = "Dallas, TX"
    pickup_date = "2026-05-30"
    pickup_time = "08:00"
    delivery_location = "Denver, CO"
    delivery_date = "2026-05-31"
    delivery_time = "09:00"
    commodity = "Steel coils"
    weight = 42000
    reference_id = "SYNTH-PARSER-001"
    equipment = "Conestoga"
    special_requirements = ["TARPS"]
    field_confidence = {"rate": "HIGH", "weight": "MEDIUM"}


def parser_output_dict():
    return {
        "source_type": "parser_dict",
        "source_file_name": "synthetic_parser_output.json",
        "broker_name": "Synthetic Parser Broker",
        "broker_mc": "SYNTH-MC-2001",
        "rate": 3300,
        "pickup_location": "Dallas, TX",
        "pickup_date": "2026-05-30",
        "pickup_time": "08:00",
        "delivery_location": "Denver, CO",
        "delivery_date": "2026-05-31",
        "delivery_time": "09:00",
        "commodity": "Steel coils",
        "weight": 42000,
        "reference_id": "SYNTH-PARSER-001",
        "equipment": "Conestoga",
        "special_requirements": ["TARPS", "APPOINTMENT_REQUIRED"],
        "field_confidence": {"rate": "HIGH", "weight": "MEDIUM"},
    }


class TestIntakeParserContract(unittest.TestCase):
    def test_normalizes_dict_parser_output_into_intake_record(self):
        record = normalize_parser_output(parser_output_dict())

        self.assertEqual(record["broker_name"], "Synthetic Parser Broker")
        self.assertEqual(record["broker_mc"], "SYNTH-MC-2001")
        self.assertEqual(record["pickup_location"], "Dallas, TX")
        self.assertEqual(record["delivery_location"], "Denver, CO")
        self.assertEqual(record["reference_id"], "SYNTH-PARSER-001")
        self.assertEqual(record["missing_fields"], [])

    def test_normalizes_object_parser_output_into_intake_record(self):
        record = normalize_parser_output(FakeParserOutput())

        self.assertEqual(record["source_type"], "parser_object")
        self.assertEqual(record["source_file_name"], "synthetic_parser_output.txt")
        self.assertEqual(record["broker_name"], "Synthetic Parser Broker")
        self.assertEqual(record["special_requirements"], ["TARPS"])

    def test_preserves_and_overrides_source_metadata(self):
        record = normalize_parser_output(
            parser_output_dict(),
            source_type="ratecon_parser_v1",
            source_file_name="synthetic_ratecon.pdf",
            received_at_utc="2026-05-29T10:00:00Z",
            intake_id="INTAKE-PARSER-1",
        )

        self.assertEqual(record["intake_id"], "INTAKE-PARSER-1")
        self.assertEqual(record["source_type"], "ratecon_parser_v1")
        self.assertEqual(record["source_file_name"], "synthetic_ratecon.pdf")
        self.assertEqual(record["received_at_utc"], "2026-05-29T10:00:00Z")

    def test_preserves_field_confidence(self):
        record = normalize_parser_output(parser_output_dict())

        self.assertEqual(
            record["field_confidence"],
            {"rate": "HIGH", "weight": "MEDIUM"},
        )

    def test_missing_fields_still_calculated(self):
        record = normalize_parser_output({"broker_name": "Synthetic Parser Broker"})

        self.assertIn("broker_mc", record["missing_fields"])
        self.assertIn("rate", record["missing_fields"])
        self.assertIn("pickup_location", record["missing_fields"])

    def test_needs_check_fields_still_calculated(self):
        record = normalize_parser_output(
            {
                "broker_name": "Synthetic Parser Broker",
                "pickup_location": "Dallas, TX",
                "delivery_location": "Denver, CO",
            }
        )

        self.assertIn("broker_mc", record["needs_check_fields"])
        self.assertIn("pickup_date", record["needs_check_fields"])
        self.assertIn("delivery_date", record["needs_check_fields"])

    def test_output_is_json_serializable(self):
        record = normalize_parser_output(parser_output_dict())

        json.dumps(record)

    def test_helper_does_not_mutate_input_dict_or_object(self):
        source_dict = parser_output_dict()
        source_before = copy.deepcopy(source_dict)
        source_object = FakeParserOutput()
        object_before = dict(source_object.__dict__)

        normalize_parser_output(source_dict, source_type="override")
        normalize_parser_output(source_object, source_file_name="override.pdf")

        self.assertEqual(source_dict, source_before)
        self.assertEqual(source_object.__dict__, object_before)

    def test_contract_does_not_import_parser_storage_or_integration_layers(self):
        source = inspect.getsource(intake_parser_contract)

        forbidden = [
            "import pypdf",
            "from pypdf",
            "PdfReader",
            "ocr",
            "import gspread",
            "from google.oauth",
            "gmail",
            "email",
            "telegram_sender",
            "telegram_notifier",
            "import dispatch_case",
            "from app.market_intelligence.dispatch_case",
            "event_logger",
            "scheduler",
            "import threading",
            "googlemaps",
            "dat",
            "load_intake",
            "open(",
            "read_text(",
            "read_bytes(",
            "write_text(",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text.lower(), source.lower())


if __name__ == "__main__":
    unittest.main()
