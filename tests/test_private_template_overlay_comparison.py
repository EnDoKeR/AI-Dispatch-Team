import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.private_template_overlay_comparison import (
    DEFAULT_TEMPLATE_OVERLAY_COMPARISON_PATH,
    build_template_overlay_comparison,
    write_template_overlay_comparison_md,
)


class PrivateTemplateOverlayComparisonTests(unittest.TestCase):
    def test_comparison_uses_status_deltas_only(self):
        baseline = {
            "template_status_counts": {"unknown": 10, "matched": 0},
            "review_required_count": 10,
            "critical_field_missing_counts": {"rate": 6},
            "conflict_counts_by_field": {"rate": 4, "pickup_location": 2},
            "blocker_category_counts": {"TEMPLATE_GAP": 10, "RESOLVER_GAP": 8, "OCR_NEEDED": 2},
        }
        overlay = {
            "template_status_counts": {"unknown": 3, "matched": 7},
            "review_required_count": 9,
            "critical_field_missing_counts": {"rate": 3},
            "conflict_counts_by_field": {"rate": 2, "pickup_location": 1},
            "blocker_category_counts": {"TEMPLATE_GAP": 3, "RESOLVER_GAP": 7, "OCR_NEEDED": 2},
        }

        comparison = build_template_overlay_comparison(baseline, overlay)
        payload = json.dumps(comparison)

        self.assertEqual(comparison["template_unknown"]["status"], "improved")
        self.assertEqual(comparison["template_matched"]["delta"], 7)
        self.assertEqual(comparison["ocr_needed"]["status"], "unchanged")
        self.assertTrue(comparison["private_values_redacted"])
        self.assertFalse(comparison["raw_text_included"])
        self.assertNotIn("FAKE BROKER LLC", payload)

    def test_write_comparison_md(self):
        comparison = build_template_overlay_comparison(
            {"template_status_counts": {"unknown": 1}},
            {"template_status_counts": {"matched": 1}},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_template_overlay_comparison_md(
                comparison,
                output_path=Path(temp_dir) / "comparison.md",
            )
            contents = path.read_text(encoding="utf-8")

        self.assertIn("template_unknown", contents)
        self.assertIn("Status deltas only", contents)
        self.assertNotIn("FAKE BROKER LLC", contents)

    def test_default_output_path_is_ignored_measurement_tree(self):
        self.assertEqual(
            DEFAULT_TEMPLATE_OVERLAY_COMPARISON_PATH,
            Path(".local_outputs/private_ratecon_measurement/template_overlay_comparison.md"),
        )


if __name__ == "__main__":
    unittest.main()
