import inspect
import json
import unittest

from app.document_ai import (
    document_record,
    document_types,
    extraction_artifacts,
    pdf_triage_contract,
)
from app.document_ai.document_record import build_document_record
from app.document_ai.document_types import (
    BOL,
    DETENTION_PROOF,
    DOCUMENT_TYPES,
    INVOICE,
    LAYOVER_PROOF,
    LUMPER_RECEIPT,
    OTHER,
    POD,
    RATE_CONFIRMATION,
    REVISED_RATE_CONFIRMATION,
    TONU_PROOF,
    UNKNOWN,
    normalize_document_type,
)
from app.document_ai.extraction_artifacts import build_extraction_artifact
from app.document_ai.pdf_triage_contract import (
    DIGITAL_TEXT,
    MANUAL_REVIEW,
    OCR_NEEDED,
    RECOMMENDED_ROUTES,
    UNSUPPORTED,
    VISION_REVIEW_CANDIDATE,
    build_pdf_triage_result,
)


class DocumentAiContractsTests(unittest.TestCase):
    def test_document_type_contract_contains_expected_values(self):
        self.assertEqual(
            DOCUMENT_TYPES,
            (
                RATE_CONFIRMATION,
                REVISED_RATE_CONFIRMATION,
                BOL,
                POD,
                LUMPER_RECEIPT,
                INVOICE,
                DETENTION_PROOF,
                LAYOVER_PROOF,
                TONU_PROOF,
                OTHER,
                UNKNOWN,
            ),
        )
        self.assertEqual(normalize_document_type("rate confirmation"), RATE_CONFIRMATION)
        self.assertEqual(normalize_document_type("not known"), UNKNOWN)

    def test_document_record_is_json_serializable(self):
        record = build_document_record(
            document_id="DOC-001",
            document_type=RATE_CONFIRMATION,
            source="manual",
            local_file_label="RATECON_001",
            page_count=2,
        )

        payload = json.loads(json.dumps(record))

        self.assertEqual(payload["document_id"], "DOC-001")
        self.assertEqual(payload["document_type"], RATE_CONFIRMATION)
        self.assertEqual(payload["privacy_classification"], "private")

    def test_triage_result_serialization_and_routes(self):
        triage = build_pdf_triage_result(
            page_count=2,
            char_count=1000,
            has_text_layer=True,
            recommended_route=DIGITAL_TEXT,
            warnings=["synthetic warning"],
        )

        payload = json.loads(json.dumps(triage))

        self.assertEqual(payload["recommended_route"], DIGITAL_TEXT)
        self.assertIn(OCR_NEEDED, RECOMMENDED_ROUTES)
        self.assertIn(VISION_REVIEW_CANDIDATE, RECOMMENDED_ROUTES)
        self.assertIn(UNSUPPORTED, RECOMMENDED_ROUTES)
        self.assertIn(MANUAL_REVIEW, RECOMMENDED_ROUTES)

    def test_unknown_triage_route_falls_back_to_manual_review(self):
        triage = build_pdf_triage_result(recommended_route="future route")

        self.assertEqual(triage["recommended_route"], MANUAL_REVIEW)

    def test_extraction_artifact_does_not_require_raw_text(self):
        artifact = build_extraction_artifact(
            document_id="DOC-001",
            method="synthetic",
            pages=[1, 2],
            text_summary="text layer present",
            word_count=100,
            block_count=10,
            table_count=1,
        )

        self.assertEqual(artifact["document_id"], "DOC-001")
        self.assertFalse(artifact["raw_text_included"])
        self.assertNotIn("raw_text", artifact)
        json.dumps(artifact)

    def test_no_forbidden_imports(self):
        modules = [
            document_types,
            document_record,
            extraction_artifacts,
            pdf_triage_contract,
        ]
        forbidden = [
            "telegram",
            "case_event_builder",
            "event_logger",
            "pypdf",
            "pdfplumber",
            "fitz",
            "pytesseract",
            "gspread",
            "googlemaps",
            "openai",
            "dat_api",
        ]

        for module in modules:
            source = inspect.getsource(module).lower()
            for term in forbidden:
                with self.subTest(module=module.__name__, term=term):
                    self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
