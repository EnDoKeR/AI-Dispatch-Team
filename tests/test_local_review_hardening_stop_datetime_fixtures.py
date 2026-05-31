import json
import unittest
from pathlib import Path


FIXTURE_DIR = (
    Path(__file__).parent
    / "fixtures"
    / "document_ai"
    / "local_review_hardening"
    / "stop_datetime"
)


class LocalReviewHardeningStopDatetimeFixtureTests(unittest.TestCase):
    def test_stop_datetime_fixtures_load(self):
        paths = sorted(FIXTURE_DIR.glob("*.json"))

        self.assertGreaterEqual(len(paths), 6)
        for path in paths:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("fixture_id", payload)
                self.assertIn("expected_span_count", payload)
                self.assertIn("expected_date_resolved", payload)
                self.assertIn("expected_time_resolved", payload)
                self.assertIn("layout_artifact", payload)

    def test_stop_datetime_fixtures_do_not_include_private_artifacts(self):
        banned_tokens = [
            ".pdf",
            ".png",
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
