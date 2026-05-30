import inspect
import json
import tempfile
import unittest

from app.document_ai import private_measurement_pipeline
from app.document_ai.private_measurement import (
    BLOCKER_CONFLICTING_CRITICAL_FIELD,
    BLOCKER_SUPPLEMENTAL_DOCUMENT_ONLY,
    BLOCKER_OCR_NEEDED,
    BLOCKER_UNSUPPORTED_OR_BROKEN_PDF,
    EXTRACTION_STATUS_EMPTY_TEXT,
    EXTRACTION_STATUS_TEXT_EXTRACTED,
)
from app.document_ai.private_measurement_pipeline import measure_private_ratecon_pdf
from app.document_ai.broker_template_registry import BrokerTemplateRegistry
from tests.fixtures.document_ai.broker_templates.fixture_loader import FIXTURE_DIR
from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import (
    write_fake_empty_text_pdf,
    write_fake_invalid_pdf,
    write_fake_text_pdf,
)
from tests.fixtures.document_ai.ratecon_text.fixture_loader import load_fixture_text
from pathlib import Path


CLASSIFICATION_FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "document_classification"
)


def load_classification_fixture(name):
    return (CLASSIFICATION_FIXTURE_DIR / name).read_text(encoding="utf-8")


class PrivateMeasurementPipelineTests(unittest.TestCase):
    def test_empty_text_pdf_routes_to_ocr_needed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = write_fake_empty_text_pdf(temp_dir)
            row = measure_private_ratecon_pdf(pdf_path, "RATECON_001")

        self.assertEqual(row["extraction_status"], EXTRACTION_STATUS_EMPTY_TEXT)
        self.assertIn(BLOCKER_OCR_NEEDED, row["blocker_categories"])
        self.assertTrue(row["review_required"])
        self.assertFalse(row["raw_text_saved"])

    def test_invalid_pdf_routes_to_unsupported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = write_fake_invalid_pdf(temp_dir)
            row = measure_private_ratecon_pdf(pdf_path, "RATECON_001")

        self.assertIn(BLOCKER_UNSUPPORTED_OR_BROKEN_PDF, row["blocker_categories"])
        self.assertEqual(row["candidate_counts_by_field"], {})
        self.assertTrue(row["review_required"])

    def test_digital_text_pdf_produces_safe_candidate_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = write_fake_text_pdf(temp_dir)
            row = measure_private_ratecon_pdf(pdf_path, "RATECON_001")

        self.assertEqual(row["extraction_status"], EXTRACTION_STATUS_TEXT_EXTRACTED)
        self.assertGreater(row["char_count"], 0)
        self.assertGreater(row["candidate_counts_by_field"].get("rate", 0), 0)
        self.assertTrue(row["private_values_redacted"])
        self.assertEqual(row["document_type"], "RATE_CONFIRMATION")
        self.assertTrue(row["ratecon_eligible"])
        self.assertTrue(row["extraction_relevant"])
        self.assertTrue(row["normal_load_movement"])

    def test_conflicting_rate_text_exposes_conflict_without_values(self):
        registry = BrokerTemplateRegistry.from_directory(FIXTURE_DIR)
        text = load_fixture_text("conflict_rate_ratecon.txt")

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = write_fake_text_pdf(temp_dir, text=text)
            row = measure_private_ratecon_pdf(pdf_path, "RATECON_001", registry)

        payload = json.dumps(row)

        self.assertIn("rate", row["conflict_fields"])
        self.assertIn(BLOCKER_CONFLICTING_CRITICAL_FIELD, row["blocker_categories"])
        self.assertNotIn("FAKE BROKER LLC", payload)
        self.assertNotIn("3200.00", payload)

    def test_row_serialization_does_not_include_raw_text_or_fake_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = write_fake_text_pdf(temp_dir)
            row = measure_private_ratecon_pdf(pdf_path, "RATECON_001")

        payload = json.dumps(row)

        self.assertNotIn("raw_text", row)
        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", payload)
        self.assertNotIn("FAKE BROKER LLC", payload)
        self.assertNotIn("FAKE-REF-001", payload)

    def test_bol_like_text_skips_ratecon_extraction_without_missing_core_fields(self):
        text = load_classification_fixture("fake_bol_scanned_like_text.txt")

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = write_fake_text_pdf(temp_dir, text=text)
            row = measure_private_ratecon_pdf(pdf_path, "RATECON_BOL")

        self.assertEqual(row["document_type"], "BILL_OF_LADING")
        self.assertFalse(row["ratecon_eligible"])
        self.assertFalse(row["extraction_relevant"])
        self.assertFalse(row["normal_load_movement"])
        self.assertTrue(row["supplemental_only"])
        self.assertEqual(row["candidate_counts_by_field"], {})
        self.assertEqual(row["missing_fields"], [])
        self.assertIn("rate", row["non_applicable_fields"])
        self.assertIn("rate", row["skipped_fields"])
        self.assertIn(BLOCKER_SUPPLEMENTAL_DOCUMENT_ONLY, row["blocker_categories"])

    def test_carrier_info_sheet_does_not_create_missing_rate_failure(self):
        text = load_classification_fixture("fake_driver_carrier_information_sheet.txt")

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = write_fake_text_pdf(temp_dir, text=text)
            row = measure_private_ratecon_pdf(pdf_path, "RATECON_INFO")

        self.assertEqual(row["document_type"], "DRIVER_CARRIER_INFO_SHEET")
        self.assertFalse(row["ratecon_eligible"])
        self.assertEqual(row["candidate_counts_by_field"], {})
        self.assertEqual(row["missing_fields"], [])
        self.assertIn("pickup_location", row["non_applicable_fields"])

    def test_main_ratecon_uses_classified_extraction_scope(self):
        text = load_classification_fixture("fake_rate_load_confirmation_main_page.txt")

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = write_fake_text_pdf(temp_dir, text=text)
            row = measure_private_ratecon_pdf(pdf_path, "RATECON_MIXED")

        self.assertTrue(row["ratecon_eligible"])
        self.assertTrue(row["extraction_relevant"])
        self.assertTrue(row["normal_load_movement"])
        self.assertIn("MAIN_RATECONF", row["page_role_counts"])
        self.assertIn("RATECON_CORE_ALLOWED", row["extraction_scope_counts"])
        self.assertGreater(row["candidate_counts_by_field"].get("rate", 0), 0)

    def test_tonu_document_is_classified_without_stop_missing_failure(self):
        text = load_classification_fixture("fake_tonu_load_confirmation.txt")

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = write_fake_text_pdf(temp_dir, text=text)
            row = measure_private_ratecon_pdf(pdf_path, "RATECON_TONU")

        self.assertEqual(row["document_type"], "TRUCK_ORDER_NOT_USED")
        self.assertTrue(row["ratecon_eligible"])
        self.assertTrue(row["extraction_relevant"])
        self.assertFalse(row["normal_load_movement"])
        self.assertIn("pickup_location", row["non_applicable_fields"])
        self.assertIn("tonu_not_normal_load_movement", row["classification_warning_codes"])

    def test_no_dispatch_decision_or_adapter_imports(self):
        source = inspect.getsource(private_measurement_pipeline)
        forbidden = [
            "DispatchCase",
            "decision_engine",
            "telegram",
            "scripts.import_ratecon",
            "scripts.read_ratecon",
            "pytesseract",
            "openai",
            "googleapiclient",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
