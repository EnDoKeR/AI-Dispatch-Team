import json
import unittest

from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    HARD_LAYOUT_FIXTURE_NAMES,
    FIXTURE_NAMES,
    build_fixture_text_artifact,
    fixture_path,
    load_fixture_text,
)


class RateConTextFixtureTests(unittest.TestCase):
    def test_fixtures_load(self):
        for name in FIXTURE_NAMES:
            with self.subTest(name=name):
                text = load_fixture_text(name)
                self.assertTrue(text.strip())

    def test_fixtures_are_fake_only(self):
        forbidden = [
            "REAL BROKER",
            "REAL CUSTOMER",
            "PRIVATE RATECON",
            "@",
            "555-",
        ]

        for name in FIXTURE_NAMES:
            text = load_fixture_text(name).upper()
            with self.subTest(name=name):
                self.assertIn("FAKE", text)
                for marker in forbidden:
                    self.assertNotIn(marker, text)

    def test_text_artifact_from_fixture(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")

        self.assertEqual(artifact["source_name"], "simple_clean_ratecon.txt")
        self.assertEqual(artifact["page_count"], 1)
        self.assertGreater(artifact["char_count"], 100)
        self.assertFalse(artifact["contains_private_text"])
        self.assertIn("FAKE BROKER LLC", artifact["full_text"])

    def test_artifact_serializes(self):
        artifact = build_fixture_text_artifact("multi_amount_ratecon.txt")

        json.dumps(artifact)

    def test_hard_layout_fixtures_load(self):
        for name in HARD_LAYOUT_FIXTURE_NAMES:
            with self.subTest(name=name):
                path = fixture_path(name)
                text = load_fixture_text(name)
                self.assertIn("hard_layouts", str(path))
                self.assertTrue(text.strip())

    def test_hard_layout_fixtures_are_fake_only(self):
        forbidden_markers = [
            "TQL",
            "CH ROBINSON",
            "LANDSTAR",
            "RXO",
            "COYOTE",
            "JB HUNT",
            "UBER FREIGHT",
            "PRIVATE RATECON",
            "DATA/PRIVATE_RATECONS",
            "C:\\",
            "@",
            "555-",
        ]

        for name in HARD_LAYOUT_FIXTURE_NAMES:
            text = load_fixture_text(name).upper()
            with self.subTest(name=name):
                self.assertIn("FAKE", text)
                for marker in forbidden_markers:
                    self.assertNotIn(marker, text)

    def test_hard_layout_page_markers_build_multiple_pages(self):
        artifact = build_fixture_text_artifact("multi_page_rate_terms_ratecon.txt")

        self.assertEqual(artifact["source_name"], "multi_page_rate_terms_ratecon.txt")
        self.assertEqual(artifact["page_count"], 2)
        self.assertFalse(artifact["contains_private_text"])
        self.assertTrue(all(page["text"] for page in artifact["pages"]))


if __name__ == "__main__":
    unittest.main()
