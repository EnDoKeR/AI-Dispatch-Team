import json
import tempfile
import unittest

from app.document_ai.document_classification import (
    CLASSIFICATION_STATUS_SUPPLEMENTAL_ONLY,
    DOCUMENT_TYPE_BILL_OF_LADING,
    PAGE_ROLE_BOL,
    PAGE_ROLE_MAIN_RATECONF,
    PAGE_ROLE_TERMS,
    SECTION_ROLE_RATE_SUMMARY,
)
from app.document_ai.layout_pipeline import extract_layout_candidates_from_pdf
from app.document_ai.layout_provider import STATUS_EXTRACTION_FAILED, STATUS_SUCCESS
from app.document_ai.ratecon_candidates import FIELD_RATE
from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import (
    write_fake_invalid_pdf,
    write_fake_text_pdf,
)


def _classification(
    ratecon_eligible=True,
    document_type="RATE_CONFIRMATION",
    page_roles=None,
    section_roles=None,
    status="ratecon_eligible",
):
    return {
        "document_type": document_type,
        "ratecon_eligible": ratecon_eligible,
        "supplemental_only": not ratecon_eligible,
        "classification_status": status,
        "page_results": [
            {
                "page_number": 1,
                "page_roles": page_roles or [PAGE_ROLE_MAIN_RATECONF],
                "primary_page_role": (page_roles or [PAGE_ROLE_MAIN_RATECONF])[0],
                "section_summaries": [
                    {"section_role": role}
                    for role in (section_roles or [SECTION_ROLE_RATE_SUMMARY])
                ],
            }
        ],
    }


class LayoutPipelineTests(unittest.TestCase):
    def test_fake_pdf_provider_to_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir, text="Rate Confirmation\nTotal Carrier Pay $1234.00")
            result = extract_layout_candidates_from_pdf(
                path,
                provider_name="pdfplumber",
                classification_result=_classification(),
                document_id="DOC-LAYOUT-PIPELINE",
            )

        self.assertEqual(result["provider_status"], STATUS_SUCCESS)
        self.assertGreaterEqual(result["candidate_counts_by_field"].get(FIELD_RATE, 0), 1)
        self.assertFalse(result["raw_text_saved"])

    def test_provider_failure_returns_no_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_invalid_pdf(temp_dir)
            result = extract_layout_candidates_from_pdf(path, provider_name="pdfplumber")

        self.assertEqual(result["provider_status"], STATUS_EXTRACTION_FAILED)
        self.assertIsNone(result["candidate_result"])
        self.assertIn("layout_provider_no_candidates", result["warning_codes"])

    def test_non_ratecon_classification_skips_core_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir, text="Bill of Lading\nTotal Carrier Pay $1234.00")
            result = extract_layout_candidates_from_pdf(
                path,
                provider_name="pdfplumber",
                classification_result=_classification(
                    ratecon_eligible=False,
                    document_type=DOCUMENT_TYPE_BILL_OF_LADING,
                    page_roles=[PAGE_ROLE_BOL],
                    section_roles=[],
                    status=CLASSIFICATION_STATUS_SUPPLEMENTAL_ONLY,
                ),
            )

        self.assertEqual(result["provider_status"], STATUS_SUCCESS)
        self.assertEqual(result["candidate_result"]["candidates"], [])
        self.assertIn("layout_extraction_skipped_by_classification", result["warning_codes"])

    def test_terms_scope_does_not_create_core_stop_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(
                temp_dir,
                text="Terms and Conditions\nPickup must be on time\nDelivery penalties may apply",
            )
            result = extract_layout_candidates_from_pdf(
                path,
                provider_name="pdfplumber",
                classification_result=_classification(
                    ratecon_eligible=False,
                    document_type="TERMS_AND_CONDITIONS",
                    page_roles=[PAGE_ROLE_TERMS],
                    section_roles=[],
                    status=CLASSIFICATION_STATUS_SUPPLEMENTAL_ONLY,
                ),
            )

        self.assertEqual(result["candidate_counts_by_field"], {})
        self.assertEqual(result["candidate_result"]["candidates"], [])

    def test_output_serializes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir, text="Total Carrier Pay $1234.00")
            result = extract_layout_candidates_from_pdf(path, provider_name="pdfplumber")

        json.dumps(result)


if __name__ == "__main__":
    unittest.main()
