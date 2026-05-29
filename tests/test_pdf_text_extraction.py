import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.market_intelligence.intake import pdf_text_extraction
from app.market_intelligence.intake.pdf_text_extraction import (
    EMPTY_TEXT,
    EXTRACTION_FAILED,
    TEXT_EXTRACTED,
    UNSUPPORTED,
    extract_pdf_text_local,
)


class FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class FakeReader:
    def __init__(self, _path):
        self.pages = [
            FakePage("Synthetic PDF page one"),
            FakePage("Synthetic PDF page two"),
        ]


class EmptyReader:
    def __init__(self, _path):
        self.pages = [FakePage("")]


class PdfTextExtractionTests(unittest.TestCase):
    def make_temp_pdf(self):
        temp_dir = tempfile.TemporaryDirectory()
        path = Path(temp_dir.name) / "synthetic.pdf"
        path.write_bytes(b"%PDF-1.4 synthetic test bytes")
        return temp_dir, path

    def test_missing_file_is_safe_failure(self):
        result = extract_pdf_text_local("missing-private-ratecon.pdf")

        self.assertEqual(result["extraction_status"], EXTRACTION_FAILED)
        self.assertIn("file_not_found", result["warnings"])
        self.assertEqual(result["text"], "")
        self.assertFalse(result["private_text_saved"])

    def test_unavailable_dependency_is_safe_failure(self):
        temp_dir, path = self.make_temp_pdf()
        self.addCleanup(temp_dir.cleanup)

        with patch.object(pdf_text_extraction, "_load_pypdf_reader", side_effect=ImportError):
            result = extract_pdf_text_local(path)

        self.assertEqual(result["extraction_status"], UNSUPPORTED)
        self.assertIn("pypdf_unavailable:ImportError", result["warnings"])
        self.assertEqual(result["text"], "")

    def test_mocked_successful_extraction_returns_text_and_metadata(self):
        temp_dir, path = self.make_temp_pdf()
        self.addCleanup(temp_dir.cleanup)

        with patch.object(pdf_text_extraction, "_load_pypdf_reader", return_value=FakeReader):
            result = extract_pdf_text_local(path)

        self.assertEqual(result["extraction_status"], TEXT_EXTRACTED)
        self.assertEqual(result["extractor_name"], "pypdf")
        self.assertEqual(result["page_count"], 2)
        self.assertIn("Synthetic PDF page one", result["text"])
        self.assertEqual(result["char_count"], len(result["text"]))

    def test_empty_extraction_returns_empty_text_status(self):
        temp_dir, path = self.make_temp_pdf()
        self.addCleanup(temp_dir.cleanup)

        with patch.object(pdf_text_extraction, "_load_pypdf_reader", return_value=EmptyReader):
            result = extract_pdf_text_local(path)

        self.assertEqual(result["extraction_status"], EMPTY_TEXT)
        self.assertEqual(result["text"], "")
        self.assertEqual(result["char_count"], 0)
        self.assertIn("no_extractable_text", result["warnings"])

    def test_unsupported_non_pdf_is_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "synthetic.txt"
            path.write_text("not a pdf")

            result = extract_pdf_text_local(path)

        self.assertEqual(result["extraction_status"], UNSUPPORTED)
        self.assertIn("unsupported_file_type", result["warnings"])

    def test_output_metadata_is_json_serializable(self):
        temp_dir, path = self.make_temp_pdf()
        self.addCleanup(temp_dir.cleanup)

        with patch.object(pdf_text_extraction, "_load_pypdf_reader", return_value=FakeReader):
            result = extract_pdf_text_local(path)

        json.dumps(result)

    def test_helper_has_no_forbidden_imports(self):
        source = inspect.getsource(pdf_text_extraction).lower()
        forbidden = [
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "pytesseract",
            "easyocr",
            "ocr",
            "gspread",
            "gmail",
            "smtplib",
            "imaplib",
            "googlemaps",
            "dat_api",
            "load_intake",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
