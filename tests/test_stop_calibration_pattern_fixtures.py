import json
import unittest
from pathlib import Path


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "stop_normalization"
    / "calibration_patterns"
)


class StopCalibrationPatternFixtureTests(unittest.TestCase):
    def test_calibration_pattern_fixtures_load(self):
        fixtures = sorted(FIXTURE_DIR.glob("*.json"))

        self.assertGreaterEqual(len(fixtures), 8)
        for path in fixtures:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(payload.get("fixture_name"))
                self.assertTrue(payload.get("expected_patterns"))
                self.assertTrue(payload.get("stop_groups") or payload.get("review_rows"))

    def test_calibration_pattern_fixtures_are_fake_only(self):
        banned_fragments = [
            "mc#",
            "real broker",
            "private broker",
            "private_ratecons",
            "documents\\ai_dispatch_private",
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
        ]

        for path in FIXTURE_DIR.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8").lower()
            for fragment in banned_fragments:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertNotIn(fragment, text)


if __name__ == "__main__":
    unittest.main()

