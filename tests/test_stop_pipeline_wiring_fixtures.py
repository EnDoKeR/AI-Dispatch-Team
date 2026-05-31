import json
import unittest
from pathlib import Path


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "stop_pipeline_wiring"
)


class StopPipelineWiringFixtureTests(unittest.TestCase):
    def test_fixture_directory_exists(self):
        self.assertTrue(FIXTURE_DIR.exists())

    def test_json_fixtures_load(self):
        names = [path.name for path in FIXTURE_DIR.glob("*.json")]

        self.assertIn("fake_mergeable_single_line_stop_section.json", names)
        self.assertIn("fake_two_mergeable_single_line_sections.json", names)
        self.assertIn("fake_non_mergeable_distinct_stops.json", names)
        self.assertIn("fake_noise_signature_lines.json", names)
        self.assertIn("fake_passthrough_should_fail.json", names)

        for path in FIXTURE_DIR.glob("*.json"):
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("fixture_name", payload)
                self.assertIn("expected", payload)
                self.assertIsInstance(payload.get("stop_groups"), list)

    def test_fixtures_are_synthetic_and_safe(self):
        forbidden_content = [
            "loadconfirmation",
            "real broker",
            "mc123",
            "mc 123",
            "123 main",
            "c:\\",
        ]
        forbidden_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

        for path in FIXTURE_DIR.rglob("*"):
            if not path.is_file():
                continue
            self.assertNotIn(path.suffix.lower(), forbidden_suffixes)
            content = path.read_text(encoding="utf-8").lower()
            for token in forbidden_content:
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, content)

    def test_expected_metadata_present(self):
        mergeable = json.loads(
            (FIXTURE_DIR / "fake_mergeable_single_line_stop_section.json").read_text(
                encoding="utf-8"
            )
        )
        passthrough = json.loads(
            (FIXTURE_DIR / "fake_passthrough_should_fail.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertTrue(
            mergeable["expected"]["post_single_line_cluster_less_than_premerge"]
        )
        self.assertFalse(passthrough["expected"]["passthrough_allowed"])


if __name__ == "__main__":
    unittest.main()
