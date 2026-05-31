import json
import unittest
from pathlib import Path


FIXTURE_DIR = (
    Path(__file__).parent
    / "fixtures"
    / "document_ai"
    / "core_field_hardening"
    / "stop_span_field_mapping"
)


class CoreFieldHardeningStopSpanFieldMappingFixtureTests(unittest.TestCase):
    def test_stop_span_field_mapping_fixtures_load(self):
        paths = sorted(FIXTURE_DIR.glob("*.json"))

        self.assertGreaterEqual(len(paths), 3)
        for path in paths:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("fixture_id", payload)
                self.assertEqual(payload["selected_target"], "stop_span_field_mapping")
                self.assertIn("initial_field_statuses", payload)
                self.assertIn("span_normalized_stop_set", payload)

    def test_stop_span_field_mapping_fixtures_do_not_include_private_artifacts(self):
        banned_tokens = [
            ".pdf",
            ".png",
            "mc#",
            "mc ",
            "documents\\",
            "documents/",
            "c:\\",
            "private_key",
            "broker llc",
        ]
        for path in FIXTURE_DIR.glob("*.json"):
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path.name):
                self.assertIn("fake", text)
                for token in banned_tokens:
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
