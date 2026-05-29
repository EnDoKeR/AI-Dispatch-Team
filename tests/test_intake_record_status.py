import inspect
import unittest

from app.market_intelligence import intake_record_status
from app.market_intelligence.intake_record_status import (
    MISSING_FIELDS,
    NEEDS_CHECK,
    READY_FOR_REVIEW,
    classify_intake_record_status,
    intake_record_ready_for_review,
)


class TestIntakeRecordStatus(unittest.TestCase):
    def test_clean_record_is_ready_for_review(self):
        record = {"missing_fields": [], "needs_check_fields": []}

        self.assertEqual(
            classify_intake_record_status(record),
            READY_FOR_REVIEW,
        )
        self.assertTrue(intake_record_ready_for_review(record))

    def test_missing_fields_record_is_missing_fields(self):
        record = {"missing_fields": ["broker_mc"], "needs_check_fields": []}

        self.assertEqual(
            classify_intake_record_status(record),
            MISSING_FIELDS,
        )
        self.assertFalse(intake_record_ready_for_review(record))

    def test_needs_check_only_record_is_needs_check(self):
        record = {"missing_fields": [], "needs_check_fields": ["broker_mc"]}

        self.assertEqual(
            classify_intake_record_status(record),
            NEEDS_CHECK,
        )
        self.assertTrue(intake_record_ready_for_review(record))

    def test_missing_fields_take_priority_over_needs_check(self):
        record = {
            "missing_fields": ["broker_mc"],
            "needs_check_fields": ["pickup_date"],
        }

        self.assertEqual(
            classify_intake_record_status(record),
            MISSING_FIELDS,
        )

    def test_safe_defaults_do_not_crash(self):
        self.assertEqual(classify_intake_record_status(None), READY_FOR_REVIEW)
        self.assertEqual(classify_intake_record_status({}), READY_FOR_REVIEW)
        self.assertTrue(intake_record_ready_for_review({}))

    def test_string_fields_are_supported_safely(self):
        self.assertEqual(
            classify_intake_record_status({"missing_fields": "broker_mc"}),
            MISSING_FIELDS,
        )
        self.assertEqual(
            classify_intake_record_status({"needs_check_fields": "broker_mc"}),
            NEEDS_CHECK,
        )

    def test_status_helper_does_not_import_forbidden_layers(self):
        source = inspect.getsource(intake_record_status).lower()

        forbidden = [
            "pypdf",
            "pdfreader",
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
            "from app.load_intake",
            "import app.load_intake",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
