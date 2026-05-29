import copy
import inspect
import json
import unittest
from unittest.mock import patch

from app.market_intelligence.intake import ratecon_pdf_dry_run
from app.market_intelligence.intake.pdf_text_extraction import (
    EMPTY_TEXT,
    EXTRACTION_FAILED,
    TEXT_EXTRACTED,
)
from app.market_intelligence.intake.ratecon_pdf_dry_run import (
    BAD_TEXT_EXTRACTION,
    NEEDS_FIELD_FIX,
    NOT_READY_FOR_PDF,
    READY_FOR_REVIEW,
    run_ratecon_pdf_dry_run,
)


CLEAN_TEXT = """
Broker: Synthetic PDF Broker
Broker MC: 000456
Rate: 3600
Pickup: Dallas, TX
Pickup Date: 2026-09-01
Pickup Time: 08:00
Delivery: Denver, CO
Delivery Date: 2026-09-03
Delivery Time: 09:00
Commodity: Synthetic steel
Weight: 40000
Reference: SYN-PDF-001
Equipment: Conestoga
Special Requirements: APPOINTMENT_REQUIRED
""".strip()

MATCHING_CASE = {
    "case_id": "CASE-PDF-001",
    "reference_id": "SYN-PDF-001",
    "broker_name": "Synthetic PDF Broker",
    "broker_mc": "000456",
    "pickup": "Dallas, TX",
    "delivery": "Denver, CO",
    "rate": 3600,
}


def extraction_result(text, status=TEXT_EXTRACTED):
    return {
        "text": text,
        "extractor_name": "fake",
        "page_count": 2,
        "char_count": len(text),
        "extraction_status": status,
        "warnings": [],
        "private_text_saved": False,
    }


class RateConPdfDryRunTests(unittest.TestCase):
    def test_successful_mocked_extraction_runs_dry_run_pipeline(self):
        with patch.object(
            ratecon_pdf_dry_run,
            "extract_pdf_text_local",
            return_value=extraction_result(CLEAN_TEXT),
        ):
            result = run_ratecon_pdf_dry_run("private.pdf", anonymized_label="RATECON_001")

        self.assertEqual(result["anonymized_label"], "RATECON_001")
        self.assertEqual(result["extraction_status"], TEXT_EXTRACTED)
        self.assertEqual(result["status"], READY_FOR_REVIEW)
        self.assertEqual(
            result["dry_run_result"]["parser_output"]["broker_name"],
            "Synthetic PDF Broker",
        )
        self.assertNotIn("text", result["extraction_metadata"])

    def test_missing_fields_from_text_become_needs_field_fix(self):
        with patch.object(
            ratecon_pdf_dry_run,
            "extract_pdf_text_local",
            return_value=extraction_result("Broker: Synthetic Missing PDF"),
        ):
            result = run_ratecon_pdf_dry_run("private.pdf")

        self.assertEqual(result["status"], NEEDS_FIELD_FIX)
        self.assertIn("broker_mc", result["dry_run_result"]["intake_summary"]["missing_fields"])

    def test_empty_extraction_returns_bad_text_extraction(self):
        with patch.object(
            ratecon_pdf_dry_run,
            "extract_pdf_text_local",
            return_value=extraction_result("", status=EMPTY_TEXT),
        ):
            result = run_ratecon_pdf_dry_run("private.pdf")

        self.assertEqual(result["status"], BAD_TEXT_EXTRACTION)
        self.assertIsNone(result["dry_run_result"])

    def test_failed_extraction_is_safe(self):
        extraction = extraction_result("", status=EXTRACTION_FAILED)
        extraction["warnings"] = ["extraction_failed:PdfReadError"]

        with patch.object(
            ratecon_pdf_dry_run,
            "extract_pdf_text_local",
            return_value=extraction,
        ):
            result = run_ratecon_pdf_dry_run("private.pdf")

        self.assertEqual(result["status"], NOT_READY_FOR_PDF)
        self.assertIn("extraction_failed:PdfReadError", result["warnings"])
        self.assertIsNone(result["dry_run_result"])

    def test_case_record_optionally_produces_link_candidate(self):
        case_record = copy.deepcopy(MATCHING_CASE)

        with patch.object(
            ratecon_pdf_dry_run,
            "extract_pdf_text_local",
            return_value=extraction_result(CLEAN_TEXT),
        ):
            result = run_ratecon_pdf_dry_run("private.pdf", case_record=case_record)

        candidate = result["dry_run_result"]["link_candidate"]
        self.assertEqual(candidate["recommended_action"], "LINK_EXISTING")
        self.assertTrue(candidate["approval_required"])

    def test_no_saving_private_text_or_case_event_side_effects(self):
        with patch.object(
            ratecon_pdf_dry_run,
            "extract_pdf_text_local",
            return_value=extraction_result(CLEAN_TEXT),
        ):
            result = run_ratecon_pdf_dry_run("private.pdf")

        self.assertFalse(result["private_text_saved"])
        self.assertFalse(result["extraction_metadata"]["private_text_saved"])
        self.assertFalse(result["cases_created"])
        self.assertFalse(result["events_written"])

    def test_output_is_json_serializable(self):
        with patch.object(
            ratecon_pdf_dry_run,
            "extract_pdf_text_local",
            return_value=extraction_result(CLEAN_TEXT),
        ):
            result = run_ratecon_pdf_dry_run("private.pdf", case_record=MATCHING_CASE)

        json.dumps(result)

    def test_does_not_mutate_case_record(self):
        case_record = copy.deepcopy(MATCHING_CASE)
        before = copy.deepcopy(case_record)

        with patch.object(
            ratecon_pdf_dry_run,
            "extract_pdf_text_local",
            return_value=extraction_result(CLEAN_TEXT),
        ):
            run_ratecon_pdf_dry_run("private.pdf", case_record=case_record)

        self.assertEqual(case_record, before)

    def test_helper_has_no_forbidden_imports(self):
        source = inspect.getsource(ratecon_pdf_dry_run).lower()
        forbidden = [
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "telegram_sender",
            "telegram_notifier",
            "pytesseract",
            "easyocr",
            "gspread",
            "gmail",
            "smtplib",
            "imaplib",
            "googlemaps",
            "dat_api",
            "load_intake",
            "write_text",
            "read_text",
            "read_bytes",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
