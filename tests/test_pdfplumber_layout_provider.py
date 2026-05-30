import contextlib
import io
import json
import tempfile
import unittest

from app.document_ai.layout_provider import (
    STATUS_EMPTY_TEXT,
    STATUS_EXTRACTION_FAILED,
    STATUS_SUCCESS,
    extract_layout_artifact,
)
from app.document_ai.pdfplumber_layout_provider import (
    PDFPLUMBER_TABLE_SETTING_PROFILES,
    TABLE_PROFILE_LINES,
    TABLE_PROFILE_TEXT_STRICT,
    extract_pdfplumber_layout,
    get_pdfplumber_table_settings,
    normalize_pdfplumber_table_profile,
)
from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import (
    FAKE_RATECON_TEXT,
    write_fake_empty_text_pdf,
    write_fake_invalid_pdf,
    write_fake_text_pdf,
)


class PdfplumberLayoutProviderTests(unittest.TestCase):
    def test_invalid_pdf_returns_safe_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_invalid_pdf(temp_dir)
            result = extract_pdfplumber_layout(path, document_id="DOC-INVALID")

        self.assertEqual(result["status"], STATUS_EXTRACTION_FAILED)
        self.assertEqual(result["error_code"], "pdfplumber_open_failed")
        self.assertFalse(result["raw_text_saved"])
        self.assertNotIn(str(path), result["safe_message"])

    def test_fake_digital_text_pdf_returns_layout_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir, text=FAKE_RATECON_TEXT)
            result = extract_pdfplumber_layout(path, document_id="DOC-TEXT")

        self.assertEqual(result["status"], STATUS_SUCCESS)
        self.assertEqual(result["page_count"], 1)
        artifact = result["artifact"]
        self.assertEqual(artifact["provider"], "pdfplumber")
        self.assertEqual(artifact["document_id"], "DOC-TEXT")
        self.assertFalse(artifact["raw_text_included"])
        self.assertTrue(artifact["private_values_redacted"])
        self.assertTrue(artifact["pages"][0]["words"])
        self.assertTrue(artifact["pages"][0]["lines"])
        json.dumps(result)

    def test_extract_layout_artifact_dispatches_to_pdfplumber(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir)
            result = extract_layout_artifact(path, provider_name="pdfplumber", document_id="DOC-DISPATCH")

        self.assertEqual(result["status"], STATUS_SUCCESS)
        self.assertEqual(result["artifact"]["source_method"], "pdfplumber_layout_v1")

    def test_no_raw_text_printed(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir, text="Rate: $1234.00")
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = extract_pdfplumber_layout(path, document_id="DOC-QUIET")

        self.assertEqual(result["status"], STATUS_SUCCESS)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_empty_text_pdf_returns_empty_text_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_empty_text_pdf(temp_dir)
            result = extract_pdfplumber_layout(path, document_id="DOC-EMPTY")

        self.assertEqual(result["status"], STATUS_EMPTY_TEXT)
        self.assertIn("no_extractable_layout_text", result["warning_codes"])
        self.assertFalse(result["raw_text_saved"])

    def test_table_extraction_path_does_not_crash_without_tables(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir, text="Total Carrier Pay $1234.00")
            result = extract_pdfplumber_layout(path, document_id="DOC-TABLE-PATH")

        self.assertEqual(result["status"], STATUS_SUCCESS)
        self.assertIn("tables", result["artifact"]["pages"][0])

    def test_pdfplumber_table_settings_profiles_exist(self):
        self.assertIn(TABLE_PROFILE_LINES, PDFPLUMBER_TABLE_SETTING_PROFILES)
        self.assertIsNone(get_pdfplumber_table_settings("default"))
        self.assertEqual(
            get_pdfplumber_table_settings(TABLE_PROFILE_LINES)["vertical_strategy"],
            "lines",
        )
        self.assertEqual(
            get_pdfplumber_table_settings(TABLE_PROFILE_TEXT_STRICT)["horizontal_strategy"],
            "text",
        )

    def test_invalid_table_profile_defaults_with_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir, text="Total Carrier Pay $1234.00")
            result = extract_pdfplumber_layout(
                path,
                document_id="DOC-TABLE-PROFILE",
                table_settings_profile="not-a-profile",
            )

        self.assertEqual(result["status"], STATUS_SUCCESS)
        self.assertEqual(result["table_settings_profile"], "default")
        self.assertIn("unsupported_pdfplumber_table_profile_defaulted", result["warning_codes"])

    def test_dispatcher_accepts_table_profile_option(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir)
            result = extract_layout_artifact(
                path,
                provider_name="pdfplumber",
                document_id="DOC-DISPATCH-PROFILE",
                table_settings_profile=TABLE_PROFILE_LINES,
            )

        self.assertEqual(result["status"], STATUS_SUCCESS)
        self.assertEqual(result["table_settings_profile"], TABLE_PROFILE_LINES)
        self.assertEqual(normalize_pdfplumber_table_profile("bad profile"), "default")


if __name__ == "__main__":
    unittest.main()
