import json
import unittest
from pathlib import Path


FIXTURE_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "document_ai" / "stop_provenance"
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


class StopProvenanceFixtureTests(unittest.TestCase):
    def test_provenance_fixtures_load(self):
        fixtures = sorted(FIXTURE_DIR.glob("fake_*.json"))

        self.assertGreaterEqual(len(fixtures), 8)
        for path in fixtures:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(payload["fixture_name"].startswith("fake_"))
                self.assertIsInstance(payload["expected_root_causes"], list)
                self.assertIsInstance(payload["expected"], dict)
                self.assertIsInstance(payload["stop_groups"], list)

    def test_provenance_fields_present_and_safe(self):
        for path in FIXTURE_DIR.glob("fake_*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for group in payload["stop_groups"]:
                with self.subTest(path=path.name, group=group.get("stop_group_id")):
                    provenance = group.get("provenance", {})
                    self.assertTrue(provenance.get("source_type"))
                    self.assertTrue(provenance.get("source_generator"))
                    self.assertIn("candidate_field_names", provenance)
                    self.assertFalse(provenance.get("raw_text_included"))
                    self.assertTrue(provenance.get("private_values_redacted"))

    def test_fixtures_contain_no_private_fragments_or_media(self):
        for path in FIXTURE_DIR.rglob("*"):
            if not path.is_file():
                continue
            with self.subTest(path=path.name):
                self.assertNotIn(path.suffix.lower(), BANNED_SUFFIXES)
            text = path.read_text(encoding="utf-8")
            for fragment in BANNED_TEXT_FRAGMENTS:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertNotIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
