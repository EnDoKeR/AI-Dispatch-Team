import json
import unittest

from app.document_ai.pdf_triage_contract import (
    DIGITAL_TEXT,
    MANUAL_REVIEW,
    OCR_NEEDED,
    PDF_KIND_BROKEN,
    PDF_KIND_DIGITAL_TEXT,
    PDF_KIND_ENCRYPTED,
    PDF_KIND_IMAGE_BASED,
    PDF_KIND_MIXED,
    PDF_KIND_UNKNOWN,
    UNSUPPORTED,
    VISION_REVIEW_CANDIDATE,
    build_pdf_page_profile,
    build_pdf_triage_result,
    infer_pdf_kind,
    normalize_pdf_kind,
    normalize_route,
)


class PdfTriageContractTests(unittest.TestCase):
    def test_pdf_kind_values_exist(self):
        self.assertEqual(normalize_pdf_kind("digital text"), PDF_KIND_DIGITAL_TEXT)
        self.assertEqual(normalize_pdf_kind("image-based"), PDF_KIND_IMAGE_BASED)
        self.assertEqual(normalize_pdf_kind("mixed"), PDF_KIND_MIXED)
        self.assertEqual(normalize_pdf_kind("encrypted"), PDF_KIND_ENCRYPTED)
        self.assertEqual(normalize_pdf_kind("broken"), PDF_KIND_BROKEN)
        self.assertEqual(normalize_pdf_kind("unexpected"), PDF_KIND_UNKNOWN)

    def test_route_values_exist(self):
        self.assertEqual(normalize_route("digital text"), DIGITAL_TEXT)
        self.assertEqual(normalize_route("ocr needed"), OCR_NEEDED)
        self.assertEqual(normalize_route("vision review candidate"), VISION_REVIEW_CANDIDATE)
        self.assertEqual(normalize_route("unsupported"), UNSUPPORTED)
        self.assertEqual(normalize_route("future route"), MANUAL_REVIEW)

    def test_minimal_pdf_triage_result_serializes(self):
        result = build_pdf_triage_result(
            document_id="DOC-001",
            file_name="fake.pdf",
            page_count=2,
            char_count=1200,
            has_text_layer=True,
            recommended_route=DIGITAL_TEXT,
        )

        payload = json.loads(json.dumps(result))

        self.assertEqual(payload["document_id"], "DOC-001")
        self.assertEqual(payload["file_name"], "fake.pdf")
        self.assertEqual(payload["page_count"], 2)
        self.assertEqual(payload["char_count"], 1200)
        self.assertEqual(payload["chars_per_page"], 600.0)
        self.assertEqual(payload["pdf_kind"], PDF_KIND_DIGITAL_TEXT)

    def test_result_does_not_require_raw_text(self):
        result = build_pdf_triage_result(page_count=1, char_count=0)

        self.assertNotIn("text", result)
        self.assertNotIn("raw_text", result)
        self.assertNotIn("extracted_text", result)

    def test_page_profiles_drive_aggregate_metrics(self):
        result = build_pdf_triage_result(
            page_profiles=[
                build_pdf_page_profile(page_number=1, char_count=500, word_count=80, has_text=True),
                build_pdf_page_profile(page_number=2, char_count=0, word_count=0, has_text=False),
            ],
            recommended_route=OCR_NEEDED,
        )

        self.assertEqual(result["page_count"], 2)
        self.assertEqual(result["char_count"], 500)
        self.assertEqual(result["chars_per_page"], 250.0)
        self.assertTrue(result["has_text_layer"])
        self.assertTrue(result["mixed_pdf"])
        self.assertEqual(result["pdf_kind"], PDF_KIND_MIXED)

    def test_empty_text_route_supported(self):
        result = build_pdf_triage_result(
            page_count=2,
            char_count=0,
            likely_image_based=True,
            recommended_route=OCR_NEEDED,
            warnings=["empty_text"],
        )

        self.assertEqual(result["recommended_route"], OCR_NEEDED)
        self.assertEqual(result["pdf_kind"], PDF_KIND_IMAGE_BASED)
        self.assertIn("empty_text", result["warnings"])

    def test_broken_route_supported(self):
        result = build_pdf_triage_result(
            broken=True,
            recommended_route=UNSUPPORTED,
            warnings=["unreadable_pdf"],
        )

        self.assertEqual(result["recommended_route"], UNSUPPORTED)
        self.assertEqual(result["pdf_kind"], PDF_KIND_BROKEN)

    def test_infer_pdf_kind_prefers_failure_states(self):
        self.assertEqual(infer_pdf_kind(has_text_layer=True, broken=True), PDF_KIND_BROKEN)
        self.assertEqual(infer_pdf_kind(has_text_layer=True, encrypted=True), PDF_KIND_ENCRYPTED)


if __name__ == "__main__":
    unittest.main()
