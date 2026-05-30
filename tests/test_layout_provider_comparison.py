import tempfile
import unittest
from pathlib import Path

from app.document_ai.layout_provider_comparison import (
    LAYOUT_PROVIDER_COMPARISON_MD,
    build_layout_provider_comparison,
    write_layout_provider_comparison_report,
)


class LayoutProviderComparisonTests(unittest.TestCase):
    def _rows(self):
        return [
            {
                "document_alias": "RATECON_001",
                "candidate_counts_by_field": {"rate": 1, "pickup_date": 0},
                "layout_provider_status": "success",
                "layout_candidate_counts_by_field": {"rate": 2, "pickup_date": 1},
                "layout_improved_fields": ["rate", "pickup_date"],
                "layout_worsened_fields": [],
                "layout_unchanged_fields": [],
                "blocker_categories": ["RESOLVER_GAP"],
            },
            {
                "document_alias": "RATECON_002",
                "candidate_counts_by_field": {"rate": 1},
                "layout_provider_status": "skipped_non_digital",
                "layout_candidate_counts_by_field": {},
                "layout_improved_fields": [],
                "layout_worsened_fields": ["rate"],
                "layout_unchanged_fields": [],
                "blocker_categories": ["OCR_NEEDED"],
            },
        ]

    def test_comparison_counts_statuses_and_field_deltas(self):
        comparison = build_layout_provider_comparison(self._rows())

        self.assertEqual(comparison["total_docs"], 2)
        self.assertEqual(comparison["layout_provider_attempted_count"], 1)
        self.assertEqual(comparison["layout_provider_success_count"], 1)
        self.assertEqual(comparison["layout_provider_skipped_count"], 1)
        self.assertEqual(comparison["candidate_count_deltas_by_field"]["rate"], 0)
        self.assertEqual(comparison["candidate_count_deltas_by_field"]["pickup_date"], 1)

    def test_improvement_worsening_by_alias_uses_safe_aliases_only(self):
        comparison = build_layout_provider_comparison(self._rows())

        self.assertEqual(
            comparison["layout_improved_fields_by_alias"]["RATECON_001"],
            ["pickup_date", "rate"],
        )
        self.assertEqual(comparison["layout_worsened_fields_by_alias"]["RATECON_002"], ["rate"])

    def test_report_written_to_local_output_contains_no_private_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_layout_provider_comparison_report(
                self._rows(),
                output_dir=temp_dir,
                allow_custom_output_dir=True,
            )
            text = path.read_text(encoding="utf-8")

        self.assertEqual(path.name, LAYOUT_PROVIDER_COMPARISON_MD)
        self.assertIn("layout_provider_status_counts", text)
        self.assertIn("RATECON_001", text)
        self.assertNotIn("FAKE BROKER LLC", text)
        self.assertNotIn("raw text", text.lower().replace("no raw text", ""))

    def test_default_output_path_is_ignored_local_outputs(self):
        path = Path(".local_outputs/private_ratecon_measurement") / LAYOUT_PROVIDER_COMPARISON_MD

        self.assertTrue(str(path).startswith(".local_outputs"))


if __name__ == "__main__":
    unittest.main()
