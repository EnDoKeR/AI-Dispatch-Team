import inspect
import json
import unittest

from app.market_intelligence.intake import ratecon_field_diagnostics
from app.market_intelligence.intake.ratecon_field_diagnostics import (
    FIELD_SIGNAL_CATEGORIES,
    detect_ratecon_field_signals,
)


FAKE_TEXT = """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Total Rate: 3000
Pickup Date: 2026-09-01
Pickup: Fake Origin City, ST
Delivery Date: 2026-09-03
Delivery: Fake Destination City, ST
Weight: 40000
Commodity: FAKE PRODUCT
Reference: FAKE-REF-001
Equipment: Conestoga
Special Requirements: Appointment required
Accessorials: Detention may apply
""".strip()


class RateConFieldDiagnosticsTests(unittest.TestCase):
    def test_detects_broker_rate_pickup_delivery_labels_from_fake_text(self):
        result = detect_ratecon_field_signals(FAKE_TEXT)
        counts = result["signal_counts"]

        self.assertGreater(counts["broker_name"], 0)
        self.assertGreater(counts["broker_mc"], 0)
        self.assertGreater(counts["rate"], 0)
        self.assertGreater(counts["pickup_location"], 0)
        self.assertGreater(counts["delivery_location"], 0)

    def test_counts_reference_labels_from_fake_text(self):
        result = detect_ratecon_field_signals("Load Number: FAKE-LOAD-001\nReference: FAKE-REF-001")

        self.assertGreaterEqual(result["signal_counts"]["reference_id"], 2)
        self.assertIn("reference_id", result["detected_categories"])

    def test_detects_accessorial_labels_from_fake_text(self):
        result = detect_ratecon_field_signals("Detention\nLayover\nLumper\nTONU\nFuel Surcharge")

        self.assertGreaterEqual(result["signal_counts"]["accessorials"], 5)
        self.assertIn("accessorials", result["detected_categories"])

    def test_empty_text_is_safe(self):
        result = detect_ratecon_field_signals("")

        self.assertFalse(result["text_present"])
        self.assertEqual(result["char_count"], 0)
        self.assertEqual(result["line_count"], 0)
        self.assertIn("empty_text", result["warnings"])
        self.assertEqual(result["detected_categories"], [])
        self.assertEqual(set(result["missing_signal_categories"]), set(FIELD_SIGNAL_CATEGORIES))

    def test_output_has_no_raw_text_or_snippets(self):
        result = detect_ratecon_field_signals(FAKE_TEXT)
        serialized = json.dumps(result)

        self.assertNotIn("FAKE BROKER LLC", serialized)
        self.assertNotIn("MC000000", serialized)
        self.assertNotIn("FAKE-REF-001", serialized)
        self.assertNotIn("Fake Origin City", serialized)

    def test_output_is_json_serializable(self):
        result = detect_ratecon_field_signals(FAKE_TEXT)

        json.dumps(result)

    def test_no_mutation_of_input_text(self):
        text = str(FAKE_TEXT)
        before = str(text)

        detect_ratecon_field_signals(text)

        self.assertEqual(text, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(ratecon_field_diagnostics).lower()
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
