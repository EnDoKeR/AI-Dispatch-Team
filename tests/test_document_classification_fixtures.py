import unittest
from pathlib import Path


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "document_classification"
)
ELIGIBILITY_FIXTURE_DIR = FIXTURE_DIR / "eligibility_calibration"

EXPECTED_FIXTURES = {
    "fake_rate_load_confirmation_main_page.txt",
    "fake_rate_load_confirmation_terms_page.txt",
    "fake_rate_load_confirmation_signature_page.txt",
    "fake_carrier_tender_route_details_page.txt",
    "fake_carrier_tender_agreed_rate_billing_page.txt",
    "fake_carrier_tender_signature_terms_page.txt",
    "fake_blue_table_ratecon_main_page.txt",
    "fake_blue_table_billing_quickpay_page.txt",
    "fake_blue_table_terms_signature_page.txt",
    "fake_mcleod_load_confirmation_page1.txt",
    "fake_mcleod_load_confirmation_page2_payment_so.txt",
    "fake_mcleod_carrier_rate_agreement_page.txt",
    "fake_order_confirmation_multi_stop.txt",
    "fake_driver_carrier_information_sheet.txt",
    "fake_bol_scanned_like_text.txt",
    "fake_billing_remittance_page.txt",
    "fake_certificate_of_signature.txt",
    "fake_tonu_load_confirmation.txt",
    "fake_unknown_document.txt",
}

EXPECTED_ELIGIBILITY_FIXTURES = {
    "fake_carrier_load_tender_route_rate.txt",
    "fake_load_tender_with_billing_page.txt",
    "fake_mcleod_order_confirmation_two_page.txt",
    "fake_truck_order_not_used_payment.txt",
    "fake_signature_certificate_only.txt",
    "fake_bol_only.txt",
    "fake_terms_only_with_many_money_amounts.txt",
    "fake_billing_quickpay_only.txt",
    "fake_carrier_agreement_only.txt",
    "fake_driver_carrier_info_only.txt",
}

BANNED_REAL_BROKER_FRAGMENTS = {
    "c.h. robinson",
    "ch robinson",
    "tql",
    "total quality logistics",
    "coyote logistics",
    "uber freight",
    "rxo",
    "landstar",
    "echo global",
    "j.b. hunt",
    "jb hunt",
}

PRIVATE_PATH_FRAGMENTS = {
    "c:\\users\\",
    "c:/users/",
    "\\documents\\ratecons",
    "/documents/ratecons",
    "private_ratecons",
}


class DocumentClassificationFixtureTests(unittest.TestCase):
    def test_all_expected_fake_classification_fixtures_exist_and_load(self):
        self.assertTrue(FIXTURE_DIR.exists())

        actual = {path.name for path in FIXTURE_DIR.glob("*.txt")}
        self.assertEqual(actual, EXPECTED_FIXTURES)

        for name in sorted(EXPECTED_FIXTURES):
            with self.subTest(name=name):
                text = (FIXTURE_DIR / name).read_text(encoding="utf-8")
                self.assertGreater(len(text.strip()), 40)

    def test_fixture_directory_does_not_commit_screenshots_or_pdfs(self):
        forbidden_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

        for path in FIXTURE_DIR.rglob("*"):
            with self.subTest(path=path.name):
                self.assertNotIn(path.suffix.lower(), forbidden_suffixes)

    def test_fixtures_do_not_contain_obvious_real_broker_names(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in FIXTURE_DIR.rglob("*.txt")
        )

        for fragment in BANNED_REAL_BROKER_FRAGMENTS:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, combined)

    def test_fixtures_do_not_contain_private_path_patterns(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in FIXTURE_DIR.rglob("*.txt")
        )

        for fragment in PRIVATE_PATH_FRAGMENTS:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, combined)

    def test_fixture_readme_declares_no_private_data_policy(self):
        readme = (FIXTURE_DIR / "README.md").read_text(encoding="utf-8").lower()

        self.assertIn("no private data", readme)
        self.assertIn("real screenshots must not be committed", readme)
        self.assertIn("fake structure-equivalent", readme)

    def test_eligibility_calibration_fixtures_exist_and_load(self):
        self.assertTrue(ELIGIBILITY_FIXTURE_DIR.exists())

        actual = {path.name for path in ELIGIBILITY_FIXTURE_DIR.glob("*.txt")}
        self.assertEqual(actual, EXPECTED_ELIGIBILITY_FIXTURES)

        for name in sorted(EXPECTED_ELIGIBILITY_FIXTURES):
            with self.subTest(name=name):
                text = (ELIGIBILITY_FIXTURE_DIR / name).read_text(encoding="utf-8")
                self.assertGreater(len(text.strip()), 40)

    def test_eligibility_calibration_readme_declares_private_data_policy(self):
        readme = (ELIGIBILITY_FIXTURE_DIR / "README.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("no private data", readme)
        self.assertIn("do not commit screenshots", readme)
        self.assertIn("mimic structure only", readme)


if __name__ == "__main__":
    unittest.main()
