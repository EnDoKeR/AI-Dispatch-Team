import json
import unittest
from pathlib import Path


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_artifacts")
EXPECTED_FIXTURES = {
    "fake_blue_table_ratecon_layout.json",
    "fake_mcleod_pu_so_layout.json",
    "fake_carrier_tender_route_details_layout.json",
    "fake_multi_stop_order_confirmation_layout.json",
    "fake_terms_billing_signature_layout.json",
    "fake_tonu_payment_layout.json",
}
BANNED_PRIVATE_MARKERS = (
    "C:\\Users\\",
    "C:\\path\\",
    "C:\\REAL\\",
    "MC#",
    "MC ",
    "USDOT",
    "PRIVATE",
    "REAL BROKER",
    "REAL CARRIER",
)


def _json_fixture_paths():
    return sorted(FIXTURE_DIR.glob("*.json"))


def _walk_strings(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)
    elif isinstance(value, str):
        yield value


class LayoutArtifactFixtureTests(unittest.TestCase):
    def test_expected_fixtures_exist(self):
        names = {path.name for path in _json_fixture_paths()}

        self.assertTrue(EXPECTED_FIXTURES.issubset(names))
        self.assertTrue((FIXTURE_DIR / "README.md").exists())

    def test_fixtures_load_and_have_required_layout_fields(self):
        for path in _json_fixture_paths():
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))

                self.assertEqual(payload["source_method"], "synthetic_fixture")
                self.assertEqual(payload["provider"], "synthetic")
                self.assertFalse(payload["raw_text_included"])
                self.assertTrue(payload["private_values_redacted"])
                self.assertGreaterEqual(payload["page_count"], 1)
                self.assertEqual(payload["page_count"], len(payload["pages"]))

                for page in payload["pages"]:
                    self.assertIn("page_number", page)
                    self.assertIn("lines", page)
                    self.assertIn("blocks", page)
                    self.assertIn("tables", page)
                    self.assertIn("page_roles", page)
                    self.assertIn("section_roles", page)

    def test_fixtures_do_not_include_private_markers(self):
        for path in _json_fixture_paths():
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                combined = "\n".join(_walk_strings(payload))

                for marker in BANNED_PRIVATE_MARKERS:
                    self.assertNotIn(marker, combined)

    def test_no_pdf_or_screenshot_fixtures_committed(self):
        banned_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
        files = [path for path in FIXTURE_DIR.rglob("*") if path.is_file()]

        self.assertFalse([path for path in files if path.suffix.lower() in banned_suffixes])

    def test_fixtures_have_candidate_relevant_roles(self):
        role_sets = {}
        for path in _json_fixture_paths():
            payload = json.loads(path.read_text(encoding="utf-8"))
            roles = set()
            sections = set()
            for page in payload["pages"]:
                roles.update(page.get("page_roles", []))
                sections.update(page.get("section_roles", []))
            role_sets[path.name] = (roles, sections)

        self.assertIn("STOP_TABLE", role_sets["fake_blue_table_ratecon_layout.json"][1])
        self.assertIn("PICKUP_SECTION", role_sets["fake_mcleod_pu_so_layout.json"][1])
        self.assertIn("MAIN_TENDER", role_sets["fake_carrier_tender_route_details_layout.json"][0])
        self.assertIn("MULTI_STOP_SECTION", role_sets["fake_multi_stop_order_confirmation_layout.json"][1])
        self.assertIn("LEGAL_TERMS", role_sets["fake_terms_billing_signature_layout.json"][1])
        self.assertIn("TONU_PAYMENT", role_sets["fake_tonu_payment_layout.json"][1])


if __name__ == "__main__":
    unittest.main()
