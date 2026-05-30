import json
import unittest
from pathlib import Path


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_association")


class LayoutAssociationFixtureTests(unittest.TestCase):
    def test_expected_fixtures_exist(self):
        names = {path.name for path in FIXTURE_DIR.glob("*.json")}

        self.assertEqual(
            names,
            {
                "fake_layout_rate_improves_but_stop_ambiguous.json",
                "fake_layout_table_stop_rows.json",
                "fake_layout_mcleod_pu_so_continuation.json",
                "fake_layout_multi_stop_order.json",
                "fake_layout_terms_money_noise.json",
                "fake_layout_location_date_cross_column_conflict.json",
                "fake_layout_strong_text_weak_layout.json",
                "fake_layout_strong_layout_weak_text.json",
            },
        )

    def test_fixtures_load_as_layout_artifacts(self):
        for path in FIXTURE_DIR.glob("*.json"):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))

                self.assertEqual(data["provider"], "synthetic")
                self.assertFalse(data["raw_text_included"])
                self.assertTrue(data["private_values_redacted"])
                self.assertGreaterEqual(data["page_count"], 1)
                self.assertEqual(len(data["pages"]), data["page_count"])
                for page in data["pages"]:
                    self.assertIn("page_number", page)
                    self.assertIn("lines", page)
                    self.assertIn("blocks", page)
                    self.assertIn("tables", page)
                    self.assertIn("page_roles", page)
                    self.assertIn("section_roles", page)

    def test_no_private_paths_pdfs_or_screenshots_committed(self):
        disallowed_suffixes = {".pdf", ".png", ".jpg", ".jpeg"}
        for path in FIXTURE_DIR.iterdir():
            self.assertNotIn(path.suffix.lower(), disallowed_suffixes)

        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in FIXTURE_DIR.glob("*")
            if path.is_file()
        )

        self.assertNotIn("C:\\", combined)
        self.assertNotIn("private_ratecons", combined.lower())
        self.assertNotIn("REAL BROKER", combined)
        self.assertNotIn("REAL MC", combined)

    def test_fixtures_cover_expected_failure_styles(self):
        combined_names = " ".join(path.name for path in FIXTURE_DIR.glob("*.json"))

        self.assertIn("stop_ambiguous", combined_names)
        self.assertIn("table_stop_rows", combined_names)
        self.assertIn("multi_stop", combined_names)
        self.assertIn("terms_money_noise", combined_names)
        self.assertIn("strong_text_weak_layout", combined_names)
        self.assertIn("strong_layout_weak_text", combined_names)


if __name__ == "__main__":
    unittest.main()
