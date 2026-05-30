import copy
import inspect
import json
import unittest

from app.market_intelligence.intake import rate_confirmation_validation
from app.market_intelligence.intake.rate_confirmation_intake import (
    STATUS_MISSING_FIELDS,
    STATUS_READY_FOR_REVIEW,
    STATUS_REVIEW_REQUIRED,
    build_field_candidate,
)
from app.market_intelligence.intake.rate_confirmation_validation import (
    rate_confirmation_ready_for_review,
    validate_rate_confirmation_intake,
)


COMPLETE_RECORD = {
    "document_id": "DOC-VALID-001",
    "broker_name": "FAKE BROKER LLC",
    "load_number": "FAKE-LOAD-001",
    "rate": 2500,
    "pickup_location": "Fake City, ST 00000",
    "pickup_date": "2026-05-30",
    "delivery_location": "Example City, ST 00000",
    "delivery_date": "2026-05-31",
    "commodity": "FAKE COMMODITY",
    "weight": 42000,
}


class RateConfirmationValidationTests(unittest.TestCase):
    def test_catches_absent_required_fields_even_when_caller_lists_are_empty(self):
        record = dict(COMPLETE_RECORD)
        record["rate"] = ""
        record["missing_fields"] = []
        record["needs_check_fields"] = []

        validation = validate_rate_confirmation_intake(record)

        self.assertEqual(validation["status"], STATUS_MISSING_FIELDS)
        self.assertIn("rate", validation["missing_fields"])
        self.assertTrue(validation["review_required"])
        self.assertFalse(rate_confirmation_ready_for_review(record))

    def test_low_confidence_rate_requires_review(self):
        record = dict(COMPLETE_RECORD)
        record["field_confidences"] = {"rate": "LOW"}

        validation = validate_rate_confirmation_intake(record)

        self.assertEqual(validation["status"], STATUS_REVIEW_REQUIRED)
        self.assertIn("rate", validation["needs_check_fields"])
        self.assertIn("rate", validation["low_confidence_fields"])

    def test_missing_pickup_date_is_missing_field(self):
        record = dict(COMPLETE_RECORD)
        record["pickup_date"] = ""

        validation = validate_rate_confirmation_intake(record)

        self.assertEqual(validation["status"], STATUS_MISSING_FIELDS)
        self.assertIn("pickup_date", validation["missing_fields"])

    def test_missing_delivery_location_is_missing_field(self):
        record = dict(COMPLETE_RECORD)
        record["delivery_location"] = ""

        validation = validate_rate_confirmation_intake(record)

        self.assertEqual(validation["status"], STATUS_MISSING_FIELDS)
        self.assertIn("delivery_location", validation["missing_fields"])

    def test_conflicting_rate_candidates_require_review(self):
        record = dict(COMPLETE_RECORD)
        record["field_candidates"] = [
            build_field_candidate(field_name="rate", normalized_value=2500),
            build_field_candidate(field_name="rate", normalized_value=2600),
        ]

        validation = validate_rate_confirmation_intake(record)

        self.assertEqual(validation["status"], STATUS_REVIEW_REQUIRED)
        self.assertIn("rate", validation["needs_check_fields"])
        self.assertIn("rate", validation["conflict_fields"])

    def test_fully_populated_intake_is_ready_for_review(self):
        validation = validate_rate_confirmation_intake(COMPLETE_RECORD)

        self.assertEqual(validation["status"], STATUS_READY_FOR_REVIEW)
        self.assertFalse(validation["review_required"])
        self.assertTrue(rate_confirmation_ready_for_review(COMPLETE_RECORD))

    def test_missing_optional_fields_are_visible_but_do_not_block_ready(self):
        validation = validate_rate_confirmation_intake(COMPLETE_RECORD)

        self.assertEqual(validation["status"], STATUS_READY_FOR_REVIEW)
        self.assertIn("broker_mc", validation["optional_missing_fields"])
        self.assertIn("equipment", validation["optional_missing_fields"])
        self.assertNotIn("broker_mc", validation["missing_fields"])
        self.assertNotIn("equipment", validation["missing_fields"])

    def test_missing_fields_take_priority_over_needs_check(self):
        record = dict(COMPLETE_RECORD)
        record["pickup_date"] = ""
        record["field_confidences"] = {"rate": "LOW"}

        validation = validate_rate_confirmation_intake(record)

        self.assertEqual(validation["status"], STATUS_MISSING_FIELDS)
        self.assertIn("pickup_date", validation["missing_fields"])
        self.assertIn("rate", validation["needs_check_fields"])

    def test_output_is_json_serializable(self):
        validation = validate_rate_confirmation_intake(COMPLETE_RECORD)

        json.dumps(validation)

    def test_does_not_mutate_input(self):
        record = copy.deepcopy(COMPLETE_RECORD)
        record["field_confidences"] = {"rate": "LOW"}
        before = copy.deepcopy(record)

        validate_rate_confirmation_intake(record)

        self.assertEqual(record, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(rate_confirmation_validation).lower()
        forbidden = [
            "telegram",
            "case_event_builder",
            "event_logger",
            "gspread",
            "googlemaps",
            "dat_api",
            "pypdf",
            "pdfplumber",
            "pytesseract",
            "openai",
            "gmail",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
