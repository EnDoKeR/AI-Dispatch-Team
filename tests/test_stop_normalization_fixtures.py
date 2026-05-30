import json
import unittest
from pathlib import Path


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "stop_normalization"
)

BANNED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
BANNED_TEXT_FRAGMENTS = [
    "C:\\Users\\",
    "Documents\\AI_Dispatch_Private",
    "MC 123",
    "MC123",
    "real broker",
    "private broker",
    "123 Main",
]


class StopNormalizationFixtureTests(unittest.TestCase):
    def test_expected_fixture_files_load(self):
        fixtures = sorted(FIXTURE_DIR.glob("fake_*.json"))

        self.assertEqual(len(fixtures), 8)
        for path in fixtures:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(payload["fixture_name"].startswith("fake_"))
                self.assertIsInstance(payload["stop_groups"], list)
                self.assertIsInstance(payload["expected"], dict)

    def test_fixtures_contain_no_banned_private_fragments(self):
        for path in FIXTURE_DIR.glob("fake_*.json"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for fragment in BANNED_TEXT_FRAGMENTS:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertNotIn(fragment, text)

    def test_no_pdfs_or_screenshots_committed(self):
        for path in FIXTURE_DIR.rglob("*"):
            if path.is_file():
                with self.subTest(path=path.name):
                    self.assertNotIn(path.suffix.lower(), BANNED_SUFFIXES)

    def test_required_expected_structures_present(self):
        required = {
            "fake_duplicate_header_stop_groups": "duplicate_removed_count",
            "fake_table_pickup_delivery_groups": "pickup_count",
            "fake_multi_stop_three_rows": "preserve_multi_stop",
            "fake_pu_so_continuation_groups": "delivery_count",
            "fake_ambiguous_stop_type_groups": "review_required",
            "fake_signature_footer_noise_groups": "noise_removed_count",
            "fake_terms_payment_noise_groups": "noise_removed_count",
            "fake_location_without_date": "no_invented_date",
        }
        for fixture_name, expected_key in required.items():
            path = FIXTURE_DIR / f"{fixture_name}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(fixture=fixture_name):
                self.assertIn(expected_key, payload["expected"])


if __name__ == "__main__":
    unittest.main()
