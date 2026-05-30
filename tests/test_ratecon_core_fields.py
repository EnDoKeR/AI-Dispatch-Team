import inspect
import json
import unittest

from app.market_intelligence.intake import ratecon_core_fields
from app.market_intelligence.intake.ratecon_core_fields import (
    CORE_REQUIRED_FIELDS,
    DEFERRED_GOOGLE_MAPS,
    NOT_FROM_RATECON,
    build_ratecon_core_field_summary,
)


COMPLETE_CORE_RECORD = {
    "customer_name": "FAKE CUSTOMER LLC",
    "load_label": "FAKE LOAD",
    "pickup_location": "Fake City, ST 00000",
    "pickup_date": "2026-12-01",
    "delivery_location": "Fake Town, ST 00000",
    "delivery_date": "2026-12-02",
    "load_number": "FAKE-LOAD-001",
    "rate": 0,
    "commodity": "FAKE PRODUCT",
    "weight": 40000,
}


class RateConCoreFieldsTests(unittest.TestCase):
    def test_core_required_fields_are_explicit_and_stable(self):
        self.assertEqual(
            CORE_REQUIRED_FIELDS,
            [
                "customer_name",
                "load_label",
                "pickup_location",
                "pickup_date",
                "delivery_location",
                "delivery_date",
                "load_number",
                "rate",
                "commodity",
                "weight",
            ],
        )

    def test_complete_core_fields_have_no_missing_core_fields(self):
        summary = build_ratecon_core_field_summary(COMPLETE_CORE_RECORD)

        self.assertEqual(summary["missing_core_fields"], [])
        self.assertTrue(summary["core_fields_present"])

    def test_broker_mc_missing_does_not_fail_core_ratecon_policy(self):
        summary = build_ratecon_core_field_summary(COMPLETE_CORE_RECORD)

        self.assertNotIn("broker_mc", summary["missing_core_fields"])
        self.assertIn("broker_mc", summary["optional_missing_fields"])

    def test_equipment_missing_does_not_fail_core_ratecon_policy(self):
        summary = build_ratecon_core_field_summary(COMPLETE_CORE_RECORD)

        self.assertNotIn("equipment", summary["missing_core_fields"])
        self.assertIn("equipment", summary["optional_missing_fields"])

    def test_loaded_miles_missing_is_deferred_not_missing(self):
        summary = build_ratecon_core_field_summary(COMPLETE_CORE_RECORD)

        self.assertNotIn("loaded_miles", summary["missing_core_fields"])
        self.assertIn("loaded_miles", summary["deferred_fields"])
        self.assertEqual(summary["miles_status"], DEFERRED_GOOGLE_MAPS)
        self.assertEqual(summary["miles_source"], NOT_FROM_RATECON)

    def test_aliases_support_existing_intake_fields(self):
        record = dict(COMPLETE_CORE_RECORD)
        record.pop("customer_name")
        record.pop("load_number")
        record["broker_name"] = "FAKE CUSTOMER LLC"
        record["reference_id"] = "FAKE-LOAD-001"

        summary = build_ratecon_core_field_summary(record)

        self.assertNotIn("customer_name", summary["missing_core_fields"])
        self.assertNotIn("load_number", summary["missing_core_fields"])

    def test_missing_rate_is_core_missing_field(self):
        record = dict(COMPLETE_CORE_RECORD)
        record["rate"] = ""
        summary = build_ratecon_core_field_summary(record)

        self.assertIn("rate", summary["missing_core_fields"])
        self.assertFalse(summary["core_fields_present"])

    def test_output_is_json_serializable(self):
        summary = build_ratecon_core_field_summary(COMPLETE_CORE_RECORD)

        json.dumps(summary)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(ratecon_core_fields).lower()
        forbidden = [
            "telegram",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "pypdf",
            "pytesseract",
            "gspread",
            "google.",
            "gmail",
            "googlemaps",
            "dat_api",
            "load_intake",
            "open(",
            "read_text",
            "write_text",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
