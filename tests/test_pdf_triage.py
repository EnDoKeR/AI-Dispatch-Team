import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.document_ai import pdf_triage
from app.document_ai.pdf_triage import triage_pdf
from app.document_ai.pdf_triage_contract import (
    DIGITAL_TEXT,
    OCR_NEEDED,
    UNSUPPORTED,
)
from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import (
    write_fake_empty_text_pdf,
    write_fake_invalid_pdf,
    write_fake_text_pdf,
)


class PdfTriageTests(unittest.TestCase):
    def test_missing_file_routes_to_unsupported(self):
        result = triage_pdf("missing_fake.pdf", document_id="DOC-MISSING")

        self.assertEqual(result["document_id"], "DOC-MISSING")
        self.assertEqual(result["recommended_route"], UNSUPPORTED)
        self.assertTrue(result["broken"])
        self.assertIn("file_not_found", result["warnings"])

    def test_invalid_pdf_routes_to_unsupported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_invalid_pdf(temp_dir)
            result = triage_pdf(path, document_id="DOC-BROKEN")

        self.assertEqual(result["recommended_route"], UNSUPPORTED)
        self.assertTrue(result["broken"])
        self.assertTrue(
            any(warning.startswith("pdf_read_failed:") for warning in result["warnings"])
        )

    def test_fake_digital_text_pdf_routes_to_digital_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir)
            result = triage_pdf(path, document_id="DOC-TEXT")

        self.assertEqual(result["document_id"], "DOC-TEXT")
        self.assertEqual(result["file_name"], "digital_text_ratecon_like.pdf")
        self.assertEqual(result["recommended_route"], DIGITAL_TEXT)
        self.assertEqual(result["page_count"], 1)
        self.assertGreater(result["char_count"], 40)
        self.assertTrue(result["has_text_layer"])
        self.assertFalse(result["likely_image_based"])
        self.assertNotIn("text", result)
        self.assertNotIn("raw_text", result)

    def test_fake_empty_text_pdf_routes_to_ocr_needed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_empty_text_pdf(temp_dir)
            result = triage_pdf(path)

        self.assertEqual(result["recommended_route"], OCR_NEEDED)
        self.assertEqual(result["page_count"], 1)
        self.assertEqual(result["char_count"], 0)
        self.assertTrue(result["likely_image_based"])
        self.assertIn("no_extractable_text", result["warnings"])

    def test_unavailable_pypdf_routes_to_manual_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir)
            with patch.object(pdf_triage, "_load_pypdf_reader", side_effect=ImportError):
                result = triage_pdf(path)

        self.assertEqual(result["recommended_route"], "MANUAL_REVIEW")
        self.assertIn("pypdf_unavailable:ImportError", result["warnings"])

    def test_non_pdf_is_unsupported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fake.txt"
            path.write_text("fake text", encoding="utf-8")
            result = triage_pdf(path)

        self.assertEqual(result["recommended_route"], UNSUPPORTED)
        self.assertTrue(result["broken"])
        self.assertIn("unsupported_file_type", result["warnings"])

    def test_no_raw_text_in_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir)
            result = triage_pdf(path)

        serialized = str(result)

        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", serialized)
        self.assertNotIn("FAKE BROKER LLC", serialized)
        self.assertNotIn("FAKE-REF-001", serialized)


if __name__ == "__main__":
    unittest.main()
