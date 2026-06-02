import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from app.document_ai.document_extraction_artifact import (
    artifact_summary,
    extract_document_artifact_from_pdf,
)
from app.document_ai.ocr_provider_contract import (
    OCR_STATUS_SUCCESS,
    build_ocr_page_result,
    build_ocr_provider_result,
    safe_ocr_provider_summary,
)
from app.document_ai.ratecon_gold_labels import evaluate_ratecon_against_gold
from app.document_ai.ratecon_shadow_audit import (
    build_candidate_summary,
    summarize_ratecon_shadow_audit_records,
)
from app.document_ai.tesseract_ocr_provider import extract_tesseract_ocr
from scripts import run_private_ratecon_measurement


class FakePage:
    mediabox = None

    def extract_text(self):
        return ""


class FakeReader:
    def __init__(self, _path):
        self.pages = [FakePage()]


class RateConShadowOcrRouteTests(unittest.TestCase):
    def test_cli_help_includes_ocr_flags_without_optional_dependencies(self):
        output = io.StringIO()
        with self.assertRaises(SystemExit) as raised:
            with redirect_stdout(output):
                run_private_ratecon_measurement.main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--ratecon-shadow-ocr-provider", output.getvalue())

    def test_ocr_contract_summary_redacts_page_text(self):
        result = build_ocr_provider_result(
            provider_name="tesseract",
            provider_requested="auto",
            available=True,
            status=OCR_STATUS_SUCCESS,
            pages=[
                build_ocr_page_result(
                    page_number=1,
                    text="PRIVATE LOAD 123",
                    status=OCR_STATUS_SUCCESS,
                )
            ],
        )

        summary = safe_ocr_provider_summary(result)

        self.assertEqual(summary["ocr_text_page_count"], 1)
        self.assertEqual(summary["pages_ocr_success"], 1)
        self.assertFalse(summary["raw_text_included"])
        self.assertNotIn("PRIVATE LOAD", json.dumps(summary))

    def test_tesseract_provider_unavailable_without_pytesseract(self):
        with patch(
            "app.document_ai.tesseract_ocr_provider.check_tesseract_ocr_dependencies",
            return_value={
                "pytesseract_installed": False,
                "tesseract_executable_found": False,
                "renderer_available": False,
                "renderers": {},
                "can_run_ocr": False,
                "windows_install_guidance": [],
            },
        ):
            result = extract_tesseract_ocr(
                "missing.pdf",
                triage_result={"page_count": 1, "ocr_required": True},
            )

        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("pytesseract is not installed.", result["errors"])

    def test_artifact_merges_ocr_text_and_keeps_safe_classification_summary(self):
        ocr_result = build_ocr_provider_result(
            provider_name="tesseract",
            provider_requested="auto",
            available=True,
            status=OCR_STATUS_SUCCESS,
            pages=[
                build_ocr_page_result(
                    page_number=1,
                    text="BILL OF LADING\nPROOF OF DELIVERY",
                    status=OCR_STATUS_SUCCESS,
                )
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "fake.pdf"
            pdf_path.write_bytes(b"%PDF-FAKE")
            with patch(
                "app.document_ai.document_extraction_artifact._load_pypdf_reader",
                return_value=FakeReader,
            ), patch(
                "app.document_ai.document_extraction_artifact._ocr_provider_result",
                return_value=ocr_result,
            ):
                artifact = extract_document_artifact_from_pdf(
                    pdf_path,
                    triage_result={
                        "document_id": "DOC-1",
                        "page_count": 1,
                        "ocr_required": True,
                    },
                    ocr_provider_name="auto",
                )

        summary = artifact_summary(artifact)
        self.assertEqual(artifact["source"], "ocr")
        self.assertIn("BILL OF LADING", artifact["full_text"])
        self.assertEqual(
            summary["ocr_document_classification"]["document_type"],
            "non_rate_confirmation",
        )
        self.assertEqual(
            summary["ocr_document_classification"]["skip_reason"],
            "bol_pod_or_delivery_document",
        )
        self.assertFalse(summary["ocr_provider_summary"]["raw_text_included"])

    def test_shadow_audit_aggregates_ocr_provider_and_candidate_counts(self):
        candidate_summary = build_candidate_summary(
            [
                {
                    "field": "load_number",
                    "value": "LOAD-123",
                    "source": "ocr",
                    "parser_name": "load_identifier_line_candidate_generator",
                    "confidence": 0.75,
                    "metadata": {"ocr_candidate": True},
                }
            ]
        )
        summary = summarize_ratecon_shadow_audit_records(
            [
                {
                    "shadow": {"success": True, "needs_review": True},
                    "triage": {},
                    "artifact_summary": {
                        "ocr_provider_summary": {
                            "provider_requested": "auto",
                            "provider_used": "tesseract",
                            "available": True,
                            "status": "success",
                            "pages_attempted": 1,
                            "pages_ocr_success": 1,
                            "ocr_text_page_count": 1,
                            "ocr_geometry_available": True,
                            "ocr_geometry_page_count": 1,
                            "ocr_word_box_count": 4,
                            "ocr_line_box_count": 1,
                            "warnings": [],
                            "errors": [],
                        },
                        "ocr_document_classification": {
                            "document_type": "rate_confirmation",
                            "skip_reason": "",
                        },
                    },
                    "candidate_summary": candidate_summary,
                    "legacy_shadow_comparison": {},
                    "failure_attribution": {},
                }
            ]
        )

        self.assertEqual(summary["ocr_provider_summary"]["docs_ocr_success"], 1)
        self.assertEqual(summary["ocr_provider_summary"]["ocr_geometry_doc_count"], 1)
        self.assertEqual(summary["ocr_provider_summary"]["ocr_word_box_count"], 4)
        self.assertEqual(summary["ocr_provider_summary"]["ocr_line_box_count"], 1)
        self.assertEqual(summary["ocr_candidate_summary"]["ocr_candidates_total"], 1)
        self.assertEqual(
            summary["ocr_candidate_summary"]["ocr_candidates_by_field"]["load_number"],
            1,
        )

    def test_gold_evaluator_counts_ocr_candidate_matches_without_raw_text(self):
        gold = {
            "schema_version": "ratecon_gold_label_v1",
            "document_id": "DOC-1",
            "file_hash": "hash-1",
            "file_name": "doc.pdf",
            "label_status": "labeled",
            "gold": {
                "document_type": "rate_confirmation",
                "load_number": {"value": "LOAD-123"},
                "total_carrier_rate": {"value": 1200.0, "currency": "USD"},
            },
        }
        audit = {
            "document_id": "DOC-1",
            "file_hash": "hash-1",
            "file_name": "doc.pdf",
            "artifact_summary": {
                "ocr_provider_summary": {"provider_requested": "auto", "status": "success"},
                "ocr_document_classification": {"document_type": "rate_confirmation"},
            },
            "shadow": {"resolved_fields": {}},
            "legacy": {},
            "private_eval_values": {
                "load_identity_candidate_inventory": [
                    {"value": "LOAD-123", "source": "ocr", "metadata_summary": {}}
                ],
                "rate_money_candidate_inventory": [
                    {"value": "$1,200.00", "source": "ocr", "metadata_summary": {}}
                ],
            },
        }

        evaluation = evaluate_ratecon_against_gold([gold], [audit])
        ocr_summary = evaluation["ocr_gold_eval_summary"]

        self.assertEqual(ocr_summary["ocr_gold_load_in_candidates"], 1)
        self.assertEqual(ocr_summary["ocr_gold_rate_in_candidates"], 1)
        self.assertFalse(ocr_summary["raw_text_printed"])
        self.assertNotIn("LOAD-123", json.dumps(ocr_summary))


if __name__ == "__main__":
    unittest.main()
