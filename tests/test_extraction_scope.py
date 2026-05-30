import unittest
from pathlib import Path

from app.document_ai.document_classification import classify_document_from_text_artifact
from app.document_ai.extraction_scope import (
    extraction_scope_warning_codes,
    select_pages_for_payment_terms,
    select_pages_for_rate_candidates,
    select_pages_for_ratecon_core,
    select_pages_for_requirements_candidates,
    select_pages_for_stop_candidates,
    should_skip_ratecon_extraction,
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


def artifact_from_fixture_names(*names, document_id="DOC_SCOPE"):
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


def page_numbers(pages):
    return [page["page_number"] for page in pages]


class ExtractionScopeTests(unittest.TestCase):
    def test_bol_is_skipped_for_ratecon_extraction(self):
        artifact = artifact_from_fixture_names("fake_bol_scanned_like_text.txt")
        classification = classify_document_from_text_artifact(artifact)

        self.assertTrue(should_skip_ratecon_extraction(classification))
        self.assertEqual(select_pages_for_ratecon_core(classification, artifact), [])
        self.assertEqual(select_pages_for_rate_candidates(classification, artifact), [])

    def test_certificate_signature_is_skipped(self):
        artifact = artifact_from_fixture_names("fake_certificate_of_signature.txt")
        classification = classify_document_from_text_artifact(artifact)

        self.assertTrue(should_skip_ratecon_extraction(classification))
        self.assertEqual(select_pages_for_stop_candidates(classification, artifact), [])

    def test_carrier_info_sheet_is_skipped(self):
        artifact = artifact_from_fixture_names("fake_driver_carrier_information_sheet.txt")
        classification = classify_document_from_text_artifact(artifact)

        self.assertTrue(should_skip_ratecon_extraction(classification))
        self.assertEqual(select_pages_for_ratecon_core(classification, artifact), [])

    def test_terms_only_skips_core_ratecon(self):
        artifact = artifact_from_fixture_names("fake_rate_load_confirmation_terms_page.txt")
        classification = classify_document_from_text_artifact(artifact)

        self.assertTrue(should_skip_ratecon_extraction(classification))
        self.assertEqual(select_pages_for_ratecon_core(classification, artifact), [])

    def test_main_ratecon_with_terms_selects_core_main_page_only(self):
        artifact = artifact_from_fixture_names(
            "fake_rate_load_confirmation_main_page.txt",
            "fake_rate_load_confirmation_terms_page.txt",
            "fake_rate_load_confirmation_signature_page.txt",
        )
        classification = classify_document_from_text_artifact(artifact)

        self.assertFalse(should_skip_ratecon_extraction(classification))
        self.assertEqual(page_numbers(select_pages_for_ratecon_core(classification, artifact)), [1])
        self.assertEqual(page_numbers(select_pages_for_stop_candidates(classification, artifact)), [1])
        self.assertEqual(page_numbers(select_pages_for_payment_terms(classification, artifact)), [1, 2])

    def test_agreed_rate_billing_page_can_contribute_rate_and_payment_terms(self):
        artifact = artifact_from_fixture_names(
            "fake_carrier_tender_route_details_page.txt",
            "fake_carrier_tender_agreed_rate_billing_page.txt",
            "fake_carrier_tender_signature_terms_page.txt",
        )
        classification = classify_document_from_text_artifact(artifact)

        self.assertEqual(page_numbers(select_pages_for_ratecon_core(classification, artifact)), [1])
        self.assertEqual(page_numbers(select_pages_for_rate_candidates(classification, artifact)), [1, 2, 3])
        self.assertEqual(page_numbers(select_pages_for_payment_terms(classification, artifact)), [2, 3])
        self.assertIn(
            "billing_payment_summary_scope_limited",
            extraction_scope_warning_codes(classification),
        )

    def test_billing_page_does_not_create_core_ratecon_scope(self):
        artifact = artifact_from_fixture_names("fake_blue_table_billing_quickpay_page.txt")
        classification = classify_document_from_text_artifact(artifact)

        self.assertEqual(select_pages_for_ratecon_core(classification, artifact), [])

    def test_signature_page_ignored_for_core_extraction(self):
        artifact = artifact_from_fixture_names(
            "fake_rate_load_confirmation_main_page.txt",
            "fake_rate_load_confirmation_signature_page.txt",
        )
        classification = classify_document_from_text_artifact(artifact)

        self.assertEqual(page_numbers(select_pages_for_ratecon_core(classification, artifact)), [1])
        self.assertEqual(page_numbers(select_pages_for_rate_candidates(classification, artifact)), [1])

    def test_special_instructions_can_feed_requirements_only(self):
        artifact = artifact_from_fixture_names("fake_rate_load_confirmation_main_page.txt")
        classification = classify_document_from_text_artifact(artifact)

        self.assertEqual(page_numbers(select_pages_for_requirements_candidates(classification, artifact)), [1])

    def test_tonu_does_not_create_stop_scope(self):
        artifact = artifact_from_fixture_names("fake_tonu_load_confirmation.txt")
        classification = classify_document_from_text_artifact(artifact)

        self.assertFalse(should_skip_ratecon_extraction(classification))
        self.assertEqual(select_pages_for_ratecon_core(classification, artifact), [])
        self.assertEqual(select_pages_for_stop_candidates(classification, artifact), [])
        self.assertEqual(page_numbers(select_pages_for_rate_candidates(classification, artifact)), [1])


if __name__ == "__main__":
    unittest.main()
