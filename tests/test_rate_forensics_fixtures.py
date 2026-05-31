import json
import unittest
from pathlib import Path


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "rate_forensics"
)


class RateForensicsFixtureTests(unittest.TestCase):
    def test_rate_forensics_fixture_metadata_loads(self):
        metadata_files = sorted(FIXTURE_DIR.glob("*.json"))

        self.assertGreaterEqual(len(metadata_files), 3)
        for path in metadata_files:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    data["selected_fix"],
                    "rate_source_priority_guardrails",
                )
                self.assertFalse(data["private_values_included"])
                self.assertIn("expected", data)

    def test_rate_forensics_fixtures_do_not_include_private_markers(self):
        banned = [
            "PRIVATE_RATECON",
            "REAL BROKER",
            "MC123",
            "SERVICE_ACCOUNT",
            "GOOGLE_CREDENTIAL",
        ]

        for path in sorted(FIXTURE_DIR.glob("*")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").upper()
                for marker in banned:
                    self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
