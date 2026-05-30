import inspect
import json
import unittest

from app.market_intelligence.intake import ratecon_layout_diagnostics
from app.market_intelligence.intake.ratecon_layout_diagnostics import (
    detect_ratecon_layout_shapes,
)


FAKE_TEXT = """
TRUCKLOAD RATE CONFIRMATION
Broker Name: FAKE BROKER LLC
Broker MC: MC000000
TOTAL: USD $0000.00
Load #: FAKE-REF-001
Shipper Information:
Address: Fake City, ST 00000
Pick Up Time: 2026-10-01 08:00
Consignee Information:
Address: Fake Town, ST 00000
Delivery Time: 2026-10-02 09:00
Commodity Description: FAKE PRODUCT
Total Weight: 40000 LBS
Trailer Type/Size: Conestoga 48
""".strip()


class RateConLayoutDiagnosticsTests(unittest.TestCase):
    def test_fake_text_creates_safe_shapes(self):
        report = detect_ratecon_layout_shapes(FAKE_TEXT)

        self.assertIn("rate", report["shapes_by_category"])
        self.assertIn("reference_id", report["shapes_by_category"])
        self.assertIn("pickup_location", report["shapes_by_category"])
        self.assertIn("delivery_location", report["shapes_by_category"])
        self.assertIn("TOTAL: USD $ <AMOUNT>", report["shape_counts_by_category"]["rate"])
        self.assertIn("load #: <ID>", report["shape_counts_by_category"]["reference_id"])

    def test_values_are_redacted_into_placeholders(self):
        report = detect_ratecon_layout_shapes(FAKE_TEXT)
        serialized = json.dumps(report)

        self.assertIn("<AMOUNT>", serialized)
        self.assertIn("<ID>", serialized)
        self.assertIn("<MC>", serialized)
        self.assertIn("<LOCATION>", serialized)
        self.assertIn("<WEIGHT>", serialized)
        self.assertIn("<EQUIPMENT>", serialized)

    def test_no_raw_fake_sensitive_values_appear_in_output(self):
        report = detect_ratecon_layout_shapes(FAKE_TEXT)
        serialized = json.dumps(report)

        forbidden = [
            "FAKE BROKER LLC",
            "MC000000",
            "FAKE-REF-001",
            "Fake City",
            "Fake Town",
            "0000.00",
            "40000",
            "Conestoga 48",
            "FAKE PRODUCT",
        ]

        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, serialized)

    def test_empty_text_safe(self):
        report = detect_ratecon_layout_shapes("")

        self.assertFalse(report["text_present"])
        self.assertEqual(report["char_count"], 0)
        self.assertEqual(report["shapes_by_category"], {})
        self.assertIn("empty_text", report["warnings"])

    def test_output_json_serializable(self):
        report = detect_ratecon_layout_shapes(FAKE_TEXT)

        json.dumps(report)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(ratecon_layout_diagnostics).lower()
        forbidden = [
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "pypdf",
            "pdfplumber",
            "fitz",
            "pytesseract",
            "easyocr",
            "gspread",
            "google.oauth",
            "gmail",
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
