import json
import unittest
from pathlib import Path


FIXTURE_DIR = (
    Path(__file__).parent
    / "fixtures"
    / "document_ai"
    / "candidate_coverage"
    / "stop_span_date"
)


class CandidateCoverageStopSpanDateFixtureTests(unittest.TestCase):
    def test_stop_span_date_fixture_manifest_loads(self):
        manifest = json.loads(
            (FIXTURE_DIR / "fixture_manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["target"], "stop_span_date_candidate_generation")
        self.assertGreaterEqual(len(manifest["fixtures"]), 6)
        for fixture in manifest["fixtures"]:
            with self.subTest(fixture=fixture["file"]):
                path = FIXTURE_DIR / fixture["file"]
                payload = json.loads(path.read_text(encoding="utf-8"))

                self.assertTrue(path.exists())
                self.assertIn("fixture_id", payload)
                self.assertIn("expected_span_count", payload)
                self.assertIn("expected_date_candidates", payload)
                self.assertIn("layout_artifact", payload)

    def test_stop_span_date_fixtures_do_not_include_private_artifacts(self):
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
        ]

        for path in FIXTURE_DIR.glob("*.json"):
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path.name):
                self.assertIn("fake", text)
                self.assertNotIn('"raw_text_included": true', text)
                for token in banned_tokens:
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
