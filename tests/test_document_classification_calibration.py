import unittest
from pathlib import Path

from app.document_ai.document_classification import (
    CLASSIFICATION_STATUS_RATECON_ELIGIBLE,
    CLASSIFICATION_STATUS_SUPPLEMENTAL_ONLY,
    DOCUMENT_TYPE_BILLING_INSTRUCTIONS,
    DOCUMENT_TYPE_BILL_OF_LADING,
    DOCUMENT_TYPE_CARRIER_LOAD_TENDER,
    DOCUMENT_TYPE_CARRIER_RATE_AGREEMENT,
    DOCUMENT_TYPE_CERTIFICATE_OF_SIGNATURE,
    DOCUMENT_TYPE_DRIVER_CARRIER_INFO_SHEET,
    DOCUMENT_TYPE_LOAD_TENDER,
    DOCUMENT_TYPE_ORDER_CONFIRMATION,
    DOCUMENT_TYPE_TERMS_AND_CONDITIONS,
    DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED,
    classify_document_from_text_artifact,
)
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "document_classification"
    / "eligibility_calibration"
)


def fixture_text(name):
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def artifact_from_fixture(name, document_id="DOC_CALIBRATION"):
    return build_text_extraction_artifact_for_candidates(
        artifact_id=f"ART-{document_id}",
        document_id=document_id,
        pages=[
            {
                "page_number": 1,
                "text": fixture_text(name),
                "source_method": "eligibility_calibration_fixture",
            }
        ],
        source_method="eligibility_calibration_fixture",
    )


class DocumentClassificationCalibrationTests(unittest.TestCase):
    def assertEligible(self, result, expected_type):
        self.assertEqual(result["document_type"], expected_type)
        self.assertTrue(result["ratecon_eligible"])
        self.assertFalse(result["supplemental_only"])
        self.assertEqual(
            result["classification_status"],
            CLASSIFICATION_STATUS_RATECON_ELIGIBLE,
        )

    def assertSupplemental(self, result, expected_type):
        self.assertEqual(result["document_type"], expected_type)
        self.assertFalse(result["ratecon_eligible"])
        self.assertTrue(result["supplemental_only"])
        self.assertEqual(
            result["classification_status"],
            CLASSIFICATION_STATUS_SUPPLEMENTAL_ONLY,
        )

    def test_carrier_load_tender_route_and_rate_is_eligible(self):
        result = classify_document_from_text_artifact(
            artifact_from_fixture("fake_carrier_load_tender_route_rate.txt")
        )

        self.assertEligible(result, DOCUMENT_TYPE_CARRIER_LOAD_TENDER)

    def test_load_tender_with_billing_section_is_still_eligible(self):
        result = classify_document_from_text_artifact(
            artifact_from_fixture("fake_load_tender_with_billing_page.txt")
        )

        self.assertEligible(result, DOCUMENT_TYPE_LOAD_TENDER)

    def test_mcleod_style_order_confirmation_is_eligible(self):
        result = classify_document_from_text_artifact(
            artifact_from_fixture("fake_mcleod_order_confirmation_two_page.txt")
        )

        self.assertEligible(result, DOCUMENT_TYPE_ORDER_CONFIRMATION)

    def test_truck_order_not_used_is_payment_relevant_not_normal_movement(self):
        result = classify_document_from_text_artifact(
            artifact_from_fixture("fake_truck_order_not_used_payment.txt")
        )

        self.assertEligible(result, DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED)
        self.assertIn("tonu_not_normal_load_movement", result["warning_codes"])

    def test_signature_certificate_only_remains_supplemental(self):
        result = classify_document_from_text_artifact(
            artifact_from_fixture("fake_signature_certificate_only.txt")
        )

        self.assertSupplemental(result, DOCUMENT_TYPE_CERTIFICATE_OF_SIGNATURE)

    def test_bol_only_remains_supplemental(self):
        result = classify_document_from_text_artifact(
            artifact_from_fixture("fake_bol_only.txt")
        )

        self.assertSupplemental(result, DOCUMENT_TYPE_BILL_OF_LADING)

    def test_terms_only_with_many_amounts_is_not_eligible(self):
        result = classify_document_from_text_artifact(
            artifact_from_fixture("fake_terms_only_with_many_money_amounts.txt")
        )

        self.assertSupplemental(result, DOCUMENT_TYPE_TERMS_AND_CONDITIONS)

    def test_billing_quickpay_only_is_not_eligible(self):
        result = classify_document_from_text_artifact(
            artifact_from_fixture("fake_billing_quickpay_only.txt")
        )

        self.assertSupplemental(result, DOCUMENT_TYPE_BILLING_INSTRUCTIONS)

    def test_carrier_agreement_only_is_not_eligible(self):
        result = classify_document_from_text_artifact(
            artifact_from_fixture("fake_carrier_agreement_only.txt")
        )

        self.assertSupplemental(result, DOCUMENT_TYPE_CARRIER_RATE_AGREEMENT)

    def test_driver_carrier_info_only_is_not_eligible(self):
        result = classify_document_from_text_artifact(
            artifact_from_fixture("fake_driver_carrier_info_only.txt")
        )

        self.assertSupplemental(result, DOCUMENT_TYPE_DRIVER_CARRIER_INFO_SHEET)


if __name__ == "__main__":
    unittest.main()
