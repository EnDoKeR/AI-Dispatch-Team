import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.private_template_pattern_collector import (
    collect_redacted_template_patterns_from_pdf,
    collect_redacted_template_patterns_from_text,
)
from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import (
    write_fake_empty_text_pdf,
    write_fake_text_pdf,
)


PRIVATE_LIKE_TEXT = """TRUCKLOAD RATE CONFIRMATION
Broker: FAKE BROKER LLC
Broker MC: MC 123456
Load #: FAKE-REF-001
Carrier Pay: $2,850.00
Pickup: Fake City, ST 00000
Pickup Date: 2026-06-01
Delivery: Example City, ST 00000
Delivery Date: 2026-06-02
Equipment: Dry Van
Weight: 42,500 lbs
Contact: test@example.com 555-111-2222
"""


class PrivateTemplatePatternCollectorTests(unittest.TestCase):
    def test_collect_clean_fake_text_pattern_summary(self):
        summary = collect_redacted_template_patterns_from_text(
            PRIVATE_LIKE_TEXT,
            document_alias="RATECON_001",
        )

        payload = json.dumps(summary)

        self.assertEqual(summary["document_alias"], "RATECON_001")
        self.assertIn("rate", summary["section_markers"])
        self.assertIn("stop", summary["section_markers"])
        self.assertTrue(summary["private_values_redacted"])
        self.assertFalse(summary["raw_text_included"])
        for forbidden in [
            "FAKE BROKER LLC",
            "123456",
            "FAKE-REF-001",
            "Fake City",
            "2,850.00",
            "test@example.com",
            "555-111-2222",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, payload)

    def test_multi_money_fake_text_is_redacted(self):
        text = "Carrier Pay: $2,850.00\nDetention: $75.00\nQuick Pay Fee: $25.00"
        summary = collect_redacted_template_patterns_from_text(text, "RATECON_002")
        payload = json.dumps(summary)

        self.assertGreaterEqual(payload.count("<MONEY>"), 3)
        self.assertNotIn("$75.00", payload)
        self.assertIn("terms", summary["section_markers"])

    def test_stop_table_fake_text_redacted(self):
        text = "Stop 1 | Pickup | Fake City, ST 00000 | 2026-06-01 | 08:00-12:00"
        summary = collect_redacted_template_patterns_from_text(text, "RATECON_003")
        payload = json.dumps(summary)

        self.assertIn("stop", summary["section_markers"])
        self.assertNotIn("Fake City", payload)
        self.assertNotIn("2026-06-01", payload)
        self.assertNotIn("08:00", payload)

    def test_empty_text_route_has_ocr_warning(self):
        summary = collect_redacted_template_patterns_from_text("", "RATECON_004")

        self.assertIn("OCR_NEEDED", summary["warning_codes"])
        self.assertIn("no_extractable_text", summary["warning_codes"])

    def test_collect_from_fake_pdf_without_raw_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(Path(temp_dir), text=PRIVATE_LIKE_TEXT)

            summary = collect_redacted_template_patterns_from_pdf(path, "RATECON_005")

        payload = json.dumps(summary)
        self.assertNotIn("FAKE BROKER LLC", payload)
        self.assertNotIn("FAKE-REF-001", payload)

    def test_collect_from_empty_fake_pdf_marks_ocr_needed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_empty_text_pdf(Path(temp_dir))

            summary = collect_redacted_template_patterns_from_pdf(path, "RATECON_006")

        self.assertIn("OCR_NEEDED", summary["warning_codes"])


if __name__ == "__main__":
    unittest.main()
