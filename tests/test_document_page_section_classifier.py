import unittest
from pathlib import Path

from app.document_ai.document_classification import (
    PAGE_ROLE_BILLING,
    PAGE_ROLE_BOL,
    PAGE_ROLE_CARRIER_INFO,
    PAGE_ROLE_CERTIFICATE_SIGNATURE,
    PAGE_ROLE_MAIN_RATECONF,
    PAGE_ROLE_MAIN_LOAD_CONFIRMATION,
    PAGE_ROLE_MAIN_TENDER,
    PAGE_ROLE_PAYMENT_SUMMARY,
    PAGE_ROLE_SIGNATURE,
    PAGE_ROLE_STOP_DETAILS,
    PAGE_ROLE_TERMS,
    PAGE_ROLE_UNKNOWN,
    SECTION_ROLE_BILLING_INSTRUCTIONS,
    SECTION_ROLE_BOL_BODY,
    SECTION_ROLE_CERTIFICATE_SIGNATURE_BLOCK,
    SECTION_ROLE_DELIVERY_SECTION,
    SECTION_ROLE_MULTI_STOP_SECTION,
    SECTION_ROLE_PAYMENT_TERMS,
    SECTION_ROLE_PICKUP_SECTION,
    SECTION_ROLE_QUICK_PAY,
    SECTION_ROLE_RATE_SUMMARY,
    SECTION_ROLE_SIGNATURE_BLOCK,
    SECTION_ROLE_STOP_TABLE,
    SECTION_ROLE_TONU_PAYMENT,
    classify_page_text,
    classify_sections_from_page_text,
)


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "document_classification"
)
ELIGIBILITY_FIXTURE_DIR = FIXTURE_DIR / "eligibility_calibration"


def fixture_text(name):
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def calibration_fixture_text(name):
    return (ELIGIBILITY_FIXTURE_DIR / name).read_text(encoding="utf-8")


def section_roles(result):
    return {
        section["section_role"]
        for section in result.get("section_summaries", [])
    }


class DocumentPageSectionClassifierTests(unittest.TestCase):
    def test_main_rate_load_confirmation_page_is_ratecon_eligible_page(self):
        result = classify_page_text(
            fixture_text("fake_rate_load_confirmation_main_page.txt"),
            page_number=1,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_MAIN_RATECONF)
        self.assertIn(PAGE_ROLE_PAYMENT_SUMMARY, result["page_roles"])
        self.assertIn(PAGE_ROLE_STOP_DETAILS, result["page_roles"])
        self.assertIn(SECTION_ROLE_RATE_SUMMARY, section_roles(result))
        self.assertIn(SECTION_ROLE_PICKUP_SECTION, section_roles(result))
        self.assertIn(SECTION_ROLE_DELIVERY_SECTION, section_roles(result))

    def test_carrier_tender_route_page_is_main_tender(self):
        result = classify_page_text(
            fixture_text("fake_carrier_tender_route_details_page.txt"),
            page_number=1,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_MAIN_TENDER)
        self.assertIn(PAGE_ROLE_STOP_DETAILS, result["page_roles"])
        self.assertIn(SECTION_ROLE_STOP_TABLE, section_roles(result))

    def test_agreed_rate_billing_page_has_payment_and_billing_roles(self):
        result = classify_page_text(
            fixture_text("fake_carrier_tender_agreed_rate_billing_page.txt"),
            page_number=2,
        )

        self.assertIn(PAGE_ROLE_PAYMENT_SUMMARY, result["page_roles"])
        self.assertIn(PAGE_ROLE_BILLING, result["page_roles"])
        self.assertIn(SECTION_ROLE_RATE_SUMMARY, section_roles(result))
        self.assertIn(SECTION_ROLE_BILLING_INSTRUCTIONS, section_roles(result))
        self.assertIn(SECTION_ROLE_QUICK_PAY, section_roles(result))

    def test_terms_page_is_not_primary_ratecon_by_itself(self):
        result = classify_page_text(
            fixture_text("fake_rate_load_confirmation_terms_page.txt"),
            page_number=2,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_TERMS)
        self.assertIn(PAGE_ROLE_PAYMENT_SUMMARY, result["page_roles"])
        self.assertIn(SECTION_ROLE_PAYMENT_TERMS, section_roles(result))

    def test_billing_page_gets_billing_and_quickpay_sections(self):
        result = classify_page_text(
            fixture_text("fake_blue_table_billing_quickpay_page.txt"),
            page_number=2,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_BILLING)
        self.assertIn(SECTION_ROLE_BILLING_INSTRUCTIONS, section_roles(result))
        self.assertIn(SECTION_ROLE_QUICK_PAY, section_roles(result))

    def test_signature_page_gets_signature_role(self):
        result = classify_page_text(
            fixture_text("fake_rate_load_confirmation_signature_page.txt"),
            page_number=3,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_SIGNATURE)
        self.assertIn(SECTION_ROLE_SIGNATURE_BLOCK, section_roles(result))

    def test_certificate_signature_page_is_certificate_signature(self):
        result = classify_page_text(
            fixture_text("fake_certificate_of_signature.txt"),
            page_number=1,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_CERTIFICATE_SIGNATURE)
        self.assertIn(SECTION_ROLE_CERTIFICATE_SIGNATURE_BLOCK, section_roles(result))

    def test_carrier_info_sheet_is_supplemental_info(self):
        result = classify_page_text(
            fixture_text("fake_driver_carrier_information_sheet.txt"),
            page_number=1,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_CARRIER_INFO)
        self.assertIn(PAGE_ROLE_CARRIER_INFO, result["page_roles"])

    def test_bol_page_is_bol_not_ratecon(self):
        result = classify_page_text(
            fixture_text("fake_bol_scanned_like_text.txt"),
            page_number=1,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_BOL)
        self.assertIn(SECTION_ROLE_BOL_BODY, section_roles(result))

    def test_tonu_page_has_tonu_payment_section(self):
        sections = classify_sections_from_page_text(
            fixture_text("fake_tonu_load_confirmation.txt"),
            page_number=1,
        )

        self.assertIn(
            SECTION_ROLE_TONU_PAYMENT,
            {section["section_role"] for section in sections},
        )

    def test_unknown_page_routes_to_unknown_review(self):
        result = classify_page_text(
            fixture_text("fake_unknown_document.txt"),
            page_number=1,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_UNKNOWN)
        self.assertIn("unknown_page_review_required", result["warning_codes"])

    def test_multi_stop_order_confirmation_returns_multi_section(self):
        result = classify_page_text(
            fixture_text("fake_order_confirmation_multi_stop.txt"),
            page_number=1,
        )

        self.assertIn(PAGE_ROLE_STOP_DETAILS, result["page_roles"])
        self.assertIn(SECTION_ROLE_MULTI_STOP_SECTION, section_roles(result))

    def test_carrier_load_tender_with_rate_confirmation_label_stays_main_tender(self):
        result = classify_page_text(
            calibration_fixture_text("fake_carrier_load_tender_route_rate.txt"),
            page_number=1,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_MAIN_TENDER)
        self.assertIn(PAGE_ROLE_MAIN_RATECONF, result["page_roles"])
        self.assertIn(PAGE_ROLE_PAYMENT_SUMMARY, result["page_roles"])

    def test_load_tender_with_billing_note_stays_main_tender(self):
        result = classify_page_text(
            calibration_fixture_text("fake_load_tender_with_billing_page.txt"),
            page_number=1,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_MAIN_TENDER)
        self.assertIn(PAGE_ROLE_BILLING, result["page_roles"])

    def test_order_confirmation_with_payment_summary_stays_main_load_confirmation(self):
        result = classify_page_text(
            calibration_fixture_text("fake_mcleod_order_confirmation_two_page.txt"),
            page_number=1,
        )

        self.assertEqual(result["primary_page_role"], PAGE_ROLE_MAIN_LOAD_CONFIRMATION)
        self.assertIn(PAGE_ROLE_PAYMENT_SUMMARY, result["page_roles"])


if __name__ == "__main__":
    unittest.main()
