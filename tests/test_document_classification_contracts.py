import json
import unittest

from app.document_ai.document_classification import (
    CLASSIFICATION_STATUS_NON_RATECON,
    CLASSIFICATION_STATUS_RATECON_ELIGIBLE,
    CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED,
    DOCUMENT_TYPE_BILL_OF_LADING,
    DOCUMENT_TYPE_RATE_CONFIRMATION,
    DOCUMENT_TYPE_UNKNOWN,
    DOCUMENT_TYPES,
    EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED,
    EXTRACTION_SCOPE_RATECON_CORE_ALLOWED,
    PAGE_ROLE_BOL,
    PAGE_ROLE_MAIN_RATECONF,
    PAGE_ROLE_PAYMENT_SUMMARY,
    PAGE_ROLES,
    SECTION_ROLE_PAYMENT_TERMS,
    SECTION_ROLE_RATE_SUMMARY,
    SECTION_ROLES,
    build_document_classification_result,
    build_page_classification_result,
    build_section_classification_result,
)


class DocumentClassificationContractTests(unittest.TestCase):
    def test_contract_contains_expected_document_page_and_section_values(self):
        self.assertIn(DOCUMENT_TYPE_RATE_CONFIRMATION, DOCUMENT_TYPES)
        self.assertIn(DOCUMENT_TYPE_BILL_OF_LADING, DOCUMENT_TYPES)
        self.assertIn(PAGE_ROLE_MAIN_RATECONF, PAGE_ROLES)
        self.assertIn(PAGE_ROLE_PAYMENT_SUMMARY, PAGE_ROLES)
        self.assertIn(SECTION_ROLE_RATE_SUMMARY, SECTION_ROLES)
        self.assertIn(SECTION_ROLE_PAYMENT_TERMS, SECTION_ROLES)

    def test_section_classification_serializes_scopes(self):
        section = build_section_classification_result(
            section_role=SECTION_ROLE_RATE_SUMMARY,
            extraction_scopes=[
                EXTRACTION_SCOPE_RATECON_CORE_ALLOWED,
                EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED,
            ],
            page_number=2,
            approximate_line_range=[10, 14],
            confidence=0.82,
            reasons=["rate label seen"],
            warning_codes=["terms_page_rate_warning"],
        )

        payload = json.loads(json.dumps(section))

        self.assertEqual(payload["section_role"], SECTION_ROLE_RATE_SUMMARY)
        self.assertEqual(
            payload["extraction_scopes"],
            [
                EXTRACTION_SCOPE_RATECON_CORE_ALLOWED,
                EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED,
            ],
        )
        self.assertEqual(payload["page_number"], 2)
        self.assertEqual(payload["approximate_line_range"], [10, 14])
        self.assertFalse("text" in payload)

    def test_page_classification_supports_multiple_roles(self):
        page = build_page_classification_result(
            page_number=1,
            page_roles=[PAGE_ROLE_MAIN_RATECONF, PAGE_ROLE_PAYMENT_SUMMARY],
            primary_page_role=PAGE_ROLE_MAIN_RATECONF,
            confidence=0.91,
            section_summaries=[
                build_section_classification_result(
                    section_role=SECTION_ROLE_RATE_SUMMARY,
                    extraction_scopes=[EXTRACTION_SCOPE_RATECON_CORE_ALLOWED],
                )
            ],
        )

        self.assertEqual(page["primary_page_role"], PAGE_ROLE_MAIN_RATECONF)
        self.assertIn(PAGE_ROLE_PAYMENT_SUMMARY, page["page_roles"])
        self.assertEqual(page["confidence_bucket"], "high")
        self.assertEqual(len(page["section_summaries"]), 1)

    def test_unknown_document_routes_to_review(self):
        result = build_document_classification_result(
            document_alias="RATECON_001",
            document_type=DOCUMENT_TYPE_UNKNOWN,
            confidence=0.0,
        )

        self.assertFalse(result["ratecon_eligible"])
        self.assertFalse(result["supplemental_only"])
        self.assertEqual(
            result["classification_status"],
            CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED,
        )
        self.assertEqual(result["document_type"], DOCUMENT_TYPE_UNKNOWN)
        self.assertFalse(result["raw_text_included"])
        self.assertTrue(result["private_values_redacted"])

    def test_non_ratecon_result_is_serializable(self):
        page = build_page_classification_result(
            page_number=1,
            page_roles=[PAGE_ROLE_BOL],
            primary_page_role=PAGE_ROLE_BOL,
            confidence=0.88,
        )
        result = build_document_classification_result(
            document_alias="DOC_001",
            document_type=DOCUMENT_TYPE_BILL_OF_LADING,
            ratecon_eligible=False,
            supplemental_only=True,
            confidence=0.88,
            page_roles=[PAGE_ROLE_BOL],
            page_results=[page],
        )

        payload = json.loads(json.dumps(result))

        self.assertEqual(payload["document_type"], DOCUMENT_TYPE_BILL_OF_LADING)
        self.assertEqual(payload["classification_status"], "supplemental_only")
        self.assertTrue(payload["supplemental_only"])
        self.assertFalse(payload["ratecon_eligible"])
        self.assertEqual(payload["page_results"][0]["primary_page_role"], PAGE_ROLE_BOL)

    def test_explicit_non_ratecon_status_is_preserved(self):
        result = build_document_classification_result(
            document_type=DOCUMENT_TYPE_BILL_OF_LADING,
            classification_status=CLASSIFICATION_STATUS_NON_RATECON,
        )

        self.assertEqual(result["classification_status"], CLASSIFICATION_STATUS_NON_RATECON)

    def test_ratecon_eligible_status_is_derived(self):
        result = build_document_classification_result(
            document_type=DOCUMENT_TYPE_RATE_CONFIRMATION,
            ratecon_eligible=True,
            page_roles=[PAGE_ROLE_MAIN_RATECONF],
        )

        self.assertEqual(result["classification_status"], CLASSIFICATION_STATUS_RATECON_ELIGIBLE)


if __name__ == "__main__":
    unittest.main()
