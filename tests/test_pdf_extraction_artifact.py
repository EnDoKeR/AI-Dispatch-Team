import json
import unittest

from app.document_ai.extraction_artifacts import METHOD_PYPDF
from app.document_ai.pdf_extraction_artifact import build_pdf_extraction_artifact
from app.document_ai.pdf_triage_contract import (
    DIGITAL_TEXT,
    OCR_NEEDED,
    UNSUPPORTED,
    build_pdf_page_profile,
    build_pdf_triage_result,
)


class PdfExtractionArtifactTests(unittest.TestCase):
    def test_artifact_built_from_digital_text_triage(self):
        triage = build_pdf_triage_result(
            document_id="DOC-001",
            page_profiles=[
                build_pdf_page_profile(page_number=1, char_count=500, word_count=80, has_text=True)
            ],
            recommended_route=DIGITAL_TEXT,
        )

        artifact = build_pdf_extraction_artifact(
            triage,
            method=METHOD_PYPDF,
            provider="local",
            extractor_version="test-v1",
        )

        self.assertEqual(artifact["document_id"], "DOC-001")
        self.assertEqual(artifact["recommended_route"], DIGITAL_TEXT)
        self.assertEqual(artifact["recommended_next_step"], "candidate_extraction_ready")
        self.assertEqual(artifact["page_count"], 1)
        self.assertEqual(artifact["char_count"], 500)
        self.assertFalse(artifact["raw_text_stored"])

    def test_artifact_built_from_ocr_needed_triage(self):
        triage = build_pdf_triage_result(
            document_id="DOC-EMPTY",
            page_count=2,
            char_count=0,
            likely_image_based=True,
            recommended_route=OCR_NEEDED,
            warnings=["no_extractable_text"],
        )

        artifact = build_pdf_extraction_artifact(
            triage,
            method=METHOD_PYPDF,
            provider="local",
            extractor_version="test-v1",
        )

        self.assertEqual(artifact["recommended_route"], OCR_NEEDED)
        self.assertEqual(artifact["recommended_next_step"], "ocr_needed_not_implemented")
        self.assertIn("no_extractable_text", artifact["warnings"])

    def test_artifact_built_from_broken_triage(self):
        triage = build_pdf_triage_result(
            document_id="DOC-BROKEN",
            broken=True,
            recommended_route=UNSUPPORTED,
            warnings=["pdf_read_failed"],
        )

        artifact = build_pdf_extraction_artifact(
            triage,
            method=METHOD_PYPDF,
            provider="local",
            extractor_version="test-v1",
        )

        self.assertEqual(artifact["recommended_route"], UNSUPPORTED)
        self.assertEqual(artifact["recommended_next_step"], "unsupported_or_broken_pdf")
        self.assertIn("pdf_read_failed", artifact["warnings"])

    def test_no_raw_text_included(self):
        triage = build_pdf_triage_result(
            document_id="DOC-001",
            char_count=100,
            page_count=1,
            recommended_route=DIGITAL_TEXT,
        )

        artifact = build_pdf_extraction_artifact(
            triage,
            method=METHOD_PYPDF,
            provider="local",
            extractor_version="test-v1",
        )

        self.assertNotIn("raw_text", artifact)
        self.assertNotIn("extracted_text", artifact)
        self.assertFalse(artifact["raw_text_stored"])
        self.assertFalse(artifact["contains_private_text"])

    def test_artifact_serializes_cleanly(self):
        triage = build_pdf_triage_result(
            document_id="DOC-001",
            char_count=100,
            page_count=1,
            recommended_route=DIGITAL_TEXT,
        )
        artifact = build_pdf_extraction_artifact(
            triage,
            method=METHOD_PYPDF,
            provider="local",
            extractor_version="test-v1",
        )

        json.dumps(artifact)


if __name__ == "__main__":
    unittest.main()
