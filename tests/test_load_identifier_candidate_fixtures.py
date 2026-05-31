import json
import unittest
from pathlib import Path


FIXTURE_DIR = (
    Path(__file__).parent
    / "fixtures"
    / "document_ai"
    / "candidate_coverage"
    / "load_identifier"
)


class LoadIdentifierCandidateFixtureTests(unittest.TestCase):
    def test_load_identifier_fixture_manifest_loads(self):
        manifest = json.loads(
            (FIXTURE_DIR / "fixture_manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["target"], "load_identifier_candidate_generation")
        self.assertGreaterEqual(len(manifest["fixtures"]), 12)
        for fixture in manifest["fixtures"]:
            with self.subTest(fixture=fixture["file"]):
                path = FIXTURE_DIR / fixture["file"]
                self.assertTrue(path.exists())
                self.assertIn("expected_identifier_type", fixture)
                self.assertIn("expected_primary_candidate", fixture)
                self.assertIn("pattern", fixture)

    def test_load_identifier_fixtures_do_not_include_private_artifacts(self):
        banned_tokens = [
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            "mc#",
            "mc ",
            "documents\\",
            "documents/",
            "c:\\",
            "private_key",
            "service_account",
        ]

        for path in FIXTURE_DIR.glob("*.txt"):
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path.name):
                self.assertIn("fake", text)
                for token in banned_tokens:
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
