import copy
import inspect
import json
import unittest

from app.market_intelligence import intake_record
from app.market_intelligence.intake_record import build_intake_record


class FakeSource:
    source_type = "ratecon_pdf"
    source_file_name = "ratecon.pdf"
    broker_name = "Acme Logistics"
    broker_mc = "123456"
    rate = 3200
    pickup_location = "Dallas, TX"
    pickup_date = "2026-05-30"
    pickup_time = "08:00"
    delivery_location = "Denver, CO"
    delivery_date = "2026-05-31"
    delivery_time = "09:00"
    commodity = "Steel coils"
    weight = 42000
    reference_id = "REF-123"
    equipment = "Conestoga"
    special_requirements = ["TARPS"]
    field_confidence = {"rate": "HIGH"}
    linked_dispatch_case_id = ""


def full_source_dict():
    return {
        "source_type": "ratecon_pdf",
        "source_file_name": "ratecon.pdf",
        "broker_name": "Acme Logistics",
        "broker_mc": "123456",
        "rate": 3200,
        "pickup_location": "Dallas, TX",
        "pickup_date": "2026-05-30",
        "pickup_time": "08:00",
        "delivery_location": "Denver, CO",
        "delivery_date": "2026-05-31",
        "delivery_time": "09:00",
        "commodity": "Steel coils",
        "weight": 42000,
        "reference_id": "REF-123",
        "equipment": "Conestoga",
        "special_requirements": ["TARPS", "APPOINTMENT_REQUIRED"],
        "field_confidence": {"rate": "HIGH", "weight": "MEDIUM"},
        "linked_dispatch_case_id": "",
    }


class TestIntakeRecord(unittest.TestCase):
    def test_builds_full_clean_record_with_no_missing_fields(self):
        record = build_intake_record(
            full_source_dict(),
            received_at_utc="2026-05-29T10:00:00Z",
            intake_id="INTAKE-1",
        )

        self.assertEqual(record["intake_id"], "INTAKE-1")
        self.assertEqual(record["source_type"], "ratecon_pdf")
        self.assertEqual(record["source_file_name"], "ratecon.pdf")
        self.assertEqual(record["received_at_utc"], "2026-05-29T10:00:00Z")
        self.assertEqual(record["broker_name"], "Acme Logistics")
        self.assertEqual(record["broker_mc"], "123456")
        self.assertEqual(record["rate"], 3200)
        self.assertEqual(record["pickup_location"], "Dallas, TX")
        self.assertEqual(record["delivery_location"], "Denver, CO")
        self.assertEqual(record["commodity"], "Steel coils")
        self.assertEqual(record["weight"], 42000)
        self.assertEqual(record["reference_id"], "REF-123")
        self.assertEqual(record["equipment"], "Conestoga")
        self.assertEqual(record["missing_fields"], [])
        self.assertEqual(record["needs_check_fields"], [])

    def test_missing_mandatory_fields_are_listed(self):
        record = build_intake_record({})

        self.assertEqual(
            record["missing_fields"],
            [
                "broker_name",
                "broker_mc",
                "rate",
                "pickup_location",
                "delivery_location",
                "pickup_date",
                "delivery_date",
                "weight",
                "commodity",
                "reference_id",
                "equipment",
            ],
        )

    def test_broker_name_without_mc_is_flagged(self):
        record = build_intake_record({"broker_name": "Acme Logistics"})

        self.assertIn("broker_mc", record["missing_fields"])
        self.assertIn("broker_mc", record["needs_check_fields"])
        self.assertNotIn("broker_name", record["missing_fields"])

    def test_broker_mc_without_broker_name_is_flagged(self):
        record = build_intake_record({"broker_mc": "123456"})

        self.assertIn("broker_name", record["missing_fields"])
        self.assertIn("broker_name", record["needs_check_fields"])
        self.assertNotIn("broker_mc", record["missing_fields"])

    def test_pickup_location_without_pickup_date_is_flagged(self):
        record = build_intake_record({"pickup_location": "Dallas, TX"})

        self.assertIn("pickup_date", record["missing_fields"])
        self.assertIn("pickup_date", record["needs_check_fields"])

    def test_delivery_location_without_delivery_date_is_flagged(self):
        record = build_intake_record({"delivery_location": "Denver, CO"})

        self.assertIn("delivery_date", record["missing_fields"])
        self.assertIn("delivery_date", record["needs_check_fields"])

    def test_special_requirements_normalizes_string_list_and_missing(self):
        string_record = build_intake_record({"special_requirements": "TARPS, OD"})
        list_record = build_intake_record({"special_requirements": ["TWIC", ""]})
        missing_record = build_intake_record({})

        self.assertEqual(string_record["special_requirements"], ["TARPS", "OD"])
        self.assertEqual(list_record["special_requirements"], ["TWIC"])
        self.assertEqual(missing_record["special_requirements"], [])

    def test_field_confidence_defaults_to_dict_and_preserves_values(self):
        default_record = build_intake_record({})
        populated_record = build_intake_record(
            {"field_confidence": {"rate": "HIGH"}}
        )

        self.assertEqual(default_record["field_confidence"], {})
        self.assertEqual(populated_record["field_confidence"], {"rate": "HIGH"})

    def test_record_is_json_serializable(self):
        record = build_intake_record(full_source_dict())

        json.dumps(record)

    def test_helper_does_not_mutate_input_dict_or_object(self):
        source_dict = full_source_dict()
        source_before = copy.deepcopy(source_dict)
        source_object = FakeSource()
        object_before = dict(source_object.__dict__)

        build_intake_record(source_dict)
        build_intake_record(source_object)

        self.assertEqual(source_dict, source_before)
        self.assertEqual(source_object.__dict__, object_before)

    def test_helper_works_with_object_input_and_dict_input(self):
        object_record = build_intake_record(FakeSource())
        dict_record = build_intake_record(full_source_dict())

        self.assertEqual(object_record["broker_name"], "Acme Logistics")
        self.assertEqual(object_record["reference_id"], "REF-123")
        self.assertEqual(dict_record["broker_name"], "Acme Logistics")
        self.assertEqual(dict_record["reference_id"], "REF-123")

    def test_safe_defaults_are_used_for_missing_fields(self):
        record = build_intake_record()

        self.assertEqual(record["intake_id"], "")
        self.assertEqual(record["source_type"], "")
        self.assertEqual(record["source_file_name"], "")
        self.assertEqual(record["received_at_utc"], "")
        self.assertEqual(record["rate"], "")
        self.assertEqual(record["weight"], "")
        self.assertEqual(record["special_requirements"], [])
        self.assertEqual(record["field_confidence"], {})
        self.assertEqual(record["linked_dispatch_case_id"], "")

    def test_helper_does_not_import_parser_storage_or_integration_layers(self):
        source = inspect.getsource(intake_record)

        forbidden = [
            "import pypdf",
            "from pypdf",
            "PdfReader",
            "import gspread",
            "from google.oauth",
            "telegram_sender",
            "telegram_notifier",
            "import dispatch_case",
            "from app.market_intelligence.dispatch_case",
            "event_logger",
            "scheduler",
            "import threading",
            "googlemaps",
            "load_intake",
            "open(",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
