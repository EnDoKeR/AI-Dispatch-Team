import json
import unittest

from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    FIXTURE_NAMES,
    build_fixture_text_artifact,
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


if __name__ == "__main__":
    unittest.main()
