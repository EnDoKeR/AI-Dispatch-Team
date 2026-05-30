import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.document_ai.layout_provider import (
    PROVIDER_CURRENT_TEXT_FALLBACK,
    PROVIDER_PDFPLUMBER,
    STATUS_DEPENDENCY_MISSING,
    STATUS_EXTRACTION_FAILED,
    STATUS_REVIEW_REQUIRED,
    LayoutProviderDependencyError,
    build_layout_provider_result,
    extract_layout_artifact,
    get_available_layout_providers,
    require_provider_dependency,
)


class LayoutProviderContractTests(unittest.TestCase):
    def test_provider_result_serializes(self):
        result = build_layout_provider_result(
            provider_name=PROVIDER_PDFPLUMBER,
            status=STATUS_REVIEW_REQUIRED,
            page_count=2,
            warning_codes=["layout_provider_not_implemented"],
            safe_message="Safe status only.",
        )

        payload = json.loads(json.dumps(result))

        self.assertEqual(payload["provider_name"], PROVIDER_PDFPLUMBER)
        self.assertEqual(payload["status"], STATUS_REVIEW_REQUIRED)
        self.assertEqual(payload["page_count"], 2)
        self.assertIn("table_settings_profile", payload)
        self.assertFalse(payload["raw_text_saved"])
        self.assertTrue(payload["private_values_redacted"])
        self.assertNotIn("raw_text", payload)

    def test_available_providers_include_pdfplumber(self):
        providers = get_available_layout_providers()

        self.assertIn(PROVIDER_PDFPLUMBER, providers)
        self.assertIn(PROVIDER_CURRENT_TEXT_FALLBACK, providers)

    def test_unknown_provider_returns_safe_result(self):
        result = extract_layout_artifact("does-not-matter.pdf", provider_name="unknown")

        self.assertEqual(result["status"], STATUS_REVIEW_REQUIRED)
        self.assertEqual(result["error_code"], "unknown_layout_provider")
        self.assertFalse(result["raw_text_saved"])

    def test_missing_input_returns_safe_failure(self):
        result = extract_layout_artifact("missing-layout-input.pdf")

        self.assertEqual(result["status"], STATUS_EXTRACTION_FAILED)
        self.assertEqual(result["error_code"], "layout_input_missing")
        self.assertNotIn("missing-layout-input.pdf", result["safe_message"])

    def test_dependency_missing_result_behavior(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_pdf = Path(temp_dir) / "fake.pdf"
            fake_pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")

            with patch(
                "app.document_ai.layout_provider.require_provider_dependency",
                side_effect=LayoutProviderDependencyError("missing"),
            ):
                result = extract_layout_artifact(fake_pdf, provider_name=PROVIDER_PDFPLUMBER)

        self.assertEqual(result["status"], STATUS_DEPENDENCY_MISSING)
        self.assertEqual(result["error_code"], "layout_provider_dependency_missing")
        self.assertFalse(result["raw_text_saved"])

    def test_require_dependency_accepts_installed_pdfplumber(self):
        self.assertTrue(require_provider_dependency(PROVIDER_PDFPLUMBER))


if __name__ == "__main__":
    unittest.main()
