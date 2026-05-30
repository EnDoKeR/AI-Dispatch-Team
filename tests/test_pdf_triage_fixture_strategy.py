import importlib.util
import tempfile
import unittest

from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import (
    FAKE_RATECON_TEXT,
    fake_invalid_pdf_bytes,
    fake_text_pdf_bytes,
    write_fake_empty_text_pdf,
    write_fake_invalid_pdf,
    write_fake_text_pdf,
)


class PdfTriageFixtureStrategyTests(unittest.TestCase):
    def test_fake_pdf_bytes_are_generated_without_committed_binary_fixture(self):
        payload = fake_text_pdf_bytes()

        self.assertTrue(payload.startswith(b"%PDF-1.4"))
        self.assertIn(b"FAKE BROKER LLC", payload)
        self.assertNotIn(b"PRIVATE", payload)

    def test_invalid_pdf_bytes_are_generated(self):
        payload = fake_invalid_pdf_bytes()

        self.assertEqual(payload, b"not a real pdf")

    def test_temp_fake_pdf_files_can_be_written(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            text_pdf = write_fake_text_pdf(temp_dir)
            empty_pdf = write_fake_empty_text_pdf(temp_dir)
            invalid_pdf = write_fake_invalid_pdf(temp_dir)

            self.assertTrue(text_pdf.exists())
            self.assertTrue(empty_pdf.exists())
            self.assertTrue(invalid_pdf.exists())
            self.assertEqual(text_pdf.suffix, ".pdf")

    def test_fake_fixture_text_has_no_private_markers(self):
        forbidden = [
            "PRIVATE",
            "REAL BROKER",
            "REAL CUSTOMER",
            "PHONE",
            "EMAIL",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, FAKE_RATECON_TEXT.upper())

    def test_fake_text_pdf_is_readable_by_pypdf_when_available(self):
        if importlib.util.find_spec("pypdf") is None:
            self.skipTest("pypdf is not available in this environment")

        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir)
            reader = PdfReader(str(path))
            text = reader.pages[0].extract_text() or ""

        self.assertIn("FAKE BROKER LLC", text)
        self.assertIn("FAKE-REF-001", text)


if __name__ == "__main__":
    unittest.main()
