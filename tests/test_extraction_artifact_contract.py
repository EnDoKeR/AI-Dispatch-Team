import json
import unittest

from app.document_ai.extraction_artifacts import (
    METHOD_OCR_FUTURE,
    METHOD_PDFPLUMBER_FUTURE,
    METHOD_PYPDF,
    METHOD_SYNTHETIC_FIXTURE,
    METHOD_VISION_FUTURE,
    build_extraction_artifact,
    normalize_method,
)


class ExtractionArtifactContractTests(unittest.TestCase):
    def test_artifact_serializes(self):
        artifact = build_extraction_artifact(
            artifact_id="ART-001",
            document_id="DOC-001",
            method=METHOD_SYNTHETIC_FIXTURE,
            provider="unit_test",
            extractor_version="test-v1",
            page_count=2,
            char_count=1200,
            text_summary="fake text layer present",
        )

        payload = json.loads(json.dumps(artifact))

        self.assertEqual(payload["artifact_id"], "ART-001")
        self.assertEqual(payload["method"], METHOD_SYNTHETIC_FIXTURE)
        self.assertEqual(payload["page_count"], 2)
        self.assertFalse(payload["raw_text_stored"])
        self.assertFalse(payload["contains_private_text"])

    def test_artifact_can_be_built_without_raw_text(self):
        artifact = build_extraction_artifact(document_id="DOC-001")

        self.assertNotIn("raw_text", artifact)
        self.assertNotIn("extracted_text", artifact)
        self.assertFalse(artifact["raw_text_stored"])
        self.assertFalse(artifact["contains_private_text"])
        self.assertFalse(artifact["raw_text_included"])

    def test_artifact_warns_when_raw_text_stored_is_true(self):
        artifact = build_extraction_artifact(
            document_id="DOC-001",
            raw_text_stored=True,
            contains_private_text=True,
        )

        self.assertTrue(artifact["raw_text_stored"])
        self.assertTrue(artifact["contains_private_text"])
        self.assertIn("raw_text_stored", artifact["warnings"])
        self.assertIn("contains_private_text", artifact["warnings"])

    def test_supported_method_values(self):
        self.assertEqual(normalize_method("pypdf"), METHOD_PYPDF)
        self.assertEqual(normalize_method("pdfplumber future"), METHOD_PDFPLUMBER_FUTURE)
        self.assertEqual(normalize_method("ocr future"), METHOD_OCR_FUTURE)
        self.assertEqual(normalize_method("vision future"), METHOD_VISION_FUTURE)
        self.assertEqual(normalize_method("synthetic fixture"), METHOD_SYNTHETIC_FIXTURE)

    def test_page_profiles_are_supported(self):
        artifact = build_extraction_artifact(
            document_id="DOC-001",
            page_profiles=[
                {
                    "page_number": 1,
                    "char_count": 100,
                    "word_count": 20,
                    "has_text": True,
                    "warnings": ["fake_warning"],
                }
            ],
        )

        self.assertEqual(artifact["page_profiles"][0]["page_number"], 1)
        self.assertEqual(artifact["page_profiles"][0]["char_count"], 100)
        self.assertTrue(artifact["page_profiles"][0]["has_text"])
        self.assertIn("fake_warning", artifact["page_profiles"][0]["warnings"])


if __name__ == "__main__":
    unittest.main()
