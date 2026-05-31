import json
import unittest
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "document_ai" / "stop_spans"


class StopSpanFixtureTests(unittest.TestCase):
    def test_all_stop_span_fixtures_load(self):
        paths = sorted(FIXTURE_DIR.glob("*.json"))

        self.assertGreaterEqual(len(paths), 10)
        for path in paths:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("fixture_id", payload)
                self.assertIn("expected_span_count", payload)
                self.assertIn("layout_artifact", payload)
                self.assertIsInstance(payload["layout_artifact"].get("pages"), list)

    def test_expected_span_counts_present(self):
        for path in FIXTURE_DIR.glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsInstance(payload["expected_span_count"], int)
            self.assertGreaterEqual(payload["expected_span_count"], 0)

    def test_fixtures_do_not_include_private_artifacts(self):
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
                for token in banned_tokens:
                    self.assertNotIn(token, text)

    def test_fixture_values_are_fake(self):
        for path in FIXTURE_DIR.glob("*.json"):
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path.name):
                self.assertIn("fake", text)
                self.assertNotIn("raw_text_included\": true", text)
                self.assertIn("private_values_redacted", text)


if __name__ == "__main__":
    unittest.main()
