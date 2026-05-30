import unittest
from pathlib import Path

from app.document_ai.document_classification import (
    CLASSIFICATION_STATUS_RATECON_ELIGIBLE,
    CLASSIFICATION_STATUS_SUPPLEMENTAL_ONLY,
    CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED,
    DOCUMENT_TYPE_BILL_OF_LADING,
    DOCUMENT_TYPE_CARRIER_LOAD_TENDER,
    DOCUMENT_TYPE_CARRIER_RATE_AGREEMENT,
    DOCUMENT_TYPE_CERTIFICATE_OF_SIGNATURE,
    DOCUMENT_TYPE_DRIVER_CARRIER_INFO_SHEET,
    DOCUMENT_TYPE_RATE_LOAD_CONFIRMATION,
    DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED,
    DOCUMENT_TYPE_UNKNOWN,
    PAGE_ROLE_BILLING,
    PAGE_ROLE_SIGNATURE,
    PAGE_ROLE_TERMS,
    classify_document_from_text_artifact,
)
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "document_classification"
)


def fixture_text(name):
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def artifact_from_fixture_names(*names, document_id="DOC_001"):
    pages = [
        {
            "page_number": index,
            "text": fixture_text(name),
            "source_method": "classification_fixture",
        }
        for index, name in enumerate(names, start=1)
    ]
    return build_text_extraction_artifact_for_candidates(
        artifact_id=f"ART-{document_id}",
        document_id=document_id,
        pages=pages,
        source_method="classification_fixture",
    )


class DocumentClassifierTests(unittest.TestCase):
    def test_main_ratecon_with_terms_and_signature_is_eligible(self):
        artifact = artifact_from_fixture_names(
            "fake_rate_load_confirmation_main_page.txt",
            "fake_rate_load_confirmation_terms_page.txt",
            "fake_rate_load_confirmation_signature_page.txt",
        )

        result = classify_document_from_text_artifact(artifact)

        self.assertEqual(result["document_type"], DOCUMENT_TYPE_RATE_LOAD_CONFIRMATION)
        self.assertTrue(result["ratecon_eligible"])
        self.assertFalse(result["supplemental_only"])
        self.assertEqual(
            result["classification_status"],
            CLASSIFICATION_STATUS_RATECON_ELIGIBLE,
        )
        self.assertIn(PAGE_ROLE_TERMS, result["page_roles"])
        self.assertIn(PAGE_ROLE_SIGNATURE, result["page_roles"])

    def test_tender_packet_is_eligible_with_roles_preserved(self):
        artifact = artifact_from_fixture_names(
            "fake_carrier_tender_route_details_page.txt",
            "fake_carrier_tender_agreed_rate_billing_page.txt",
            "fake_carrier_tender_signature_terms_page.txt",
        )

        result = classify_document_from_text_artifact(artifact)

        self.assertEqual(result["document_type"], DOCUMENT_TYPE_CARRIER_LOAD_TENDER)
        self.assertTrue(result["ratecon_eligible"])
        self.assertIn(PAGE_ROLE_BILLING, result["page_roles"])
        self.assertIn(PAGE_ROLE_TERMS, result["page_roles"])

    def test_terms_only_is_supplemental(self):
        artifact = artifact_from_fixture_names("fake_rate_load_confirmation_terms_page.txt")

        result = classify_document_from_text_artifact(artifact)

        self.assertFalse(result["ratecon_eligible"])
        self.assertTrue(result["supplemental_only"])
        self.assertEqual(
            result["classification_status"],
            CLASSIFICATION_STATUS_SUPPLEMENTAL_ONLY,
        )

    def test_carrier_rate_agreement_only_is_supplemental(self):
        artifact = artifact_from_fixture_names("fake_mcleod_carrier_rate_agreement_page.txt")

        result = classify_document_from_text_artifact(artifact)

        self.assertEqual(result["document_type"], DOCUMENT_TYPE_CARRIER_RATE_AGREEMENT)
        self.assertFalse(result["ratecon_eligible"])
        self.assertTrue(result["supplemental_only"])

    def test_bol_is_supplemental_not_ratecon(self):
        artifact = artifact_from_fixture_names("fake_bol_scanned_like_text.txt")

        result = classify_document_from_text_artifact(artifact)

        self.assertEqual(result["document_type"], DOCUMENT_TYPE_BILL_OF_LADING)
        self.assertFalse(result["ratecon_eligible"])
        self.assertTrue(result["supplemental_only"])

    def test_carrier_info_sheet_is_supplemental(self):
        artifact = artifact_from_fixture_names("fake_driver_carrier_information_sheet.txt")

        result = classify_document_from_text_artifact(artifact)

        self.assertEqual(result["document_type"], DOCUMENT_TYPE_DRIVER_CARRIER_INFO_SHEET)
        self.assertFalse(result["ratecon_eligible"])
        self.assertTrue(result["supplemental_only"])

    def test_certificate_signature_is_supplemental(self):
        artifact = artifact_from_fixture_names("fake_certificate_of_signature.txt")

        result = classify_document_from_text_artifact(artifact)

        self.assertEqual(result["document_type"], DOCUMENT_TYPE_CERTIFICATE_OF_SIGNATURE)
        self.assertFalse(result["ratecon_eligible"])
        self.assertTrue(result["supplemental_only"])

    def test_tonu_is_classified_separately_and_eligible_for_payment_review(self):
        artifact = artifact_from_fixture_names("fake_tonu_load_confirmation.txt")

        result = classify_document_from_text_artifact(artifact)

        self.assertEqual(result["document_type"], DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED)
        self.assertTrue(result["ratecon_eligible"])
        self.assertIn("tonu_not_normal_load_movement", result["warning_codes"])

    def test_unknown_routes_to_review(self):
        artifact = artifact_from_fixture_names("fake_unknown_document.txt")

        result = classify_document_from_text_artifact(artifact)

        self.assertEqual(result["document_type"], DOCUMENT_TYPE_UNKNOWN)
        self.assertFalse(result["ratecon_eligible"])
        self.assertEqual(
            result["classification_status"],
            CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED,
        )

    def test_empty_text_routes_to_unknown_review_required(self):
        artifact = build_text_extraction_artifact_for_candidates(
            artifact_id="ART-EMPTY",
            document_id="DOC_EMPTY",
            pages=[],
            source_method="classification_fixture",
        )

        result = classify_document_from_text_artifact(artifact)

        self.assertEqual(result["document_type"], DOCUMENT_TYPE_UNKNOWN)
        self.assertIn("ocr_required_or_empty_text", result["warning_codes"])


if __name__ == "__main__":
    unittest.main()
