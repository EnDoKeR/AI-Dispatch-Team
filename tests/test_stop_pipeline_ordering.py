import json
import unittest
from pathlib import Path

from app.document_ai.stop_association import build_stop_association_result
from app.document_ai.stop_normalization import build_normalized_stop_set


PROVENANCE_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "document_ai" / "stop_provenance"
)


def _load(name):
    return json.loads((PROVENANCE_DIR / f"{name}.json").read_text(encoding="utf-8"))


class StopPipelineOrderingTests(unittest.TestCase):
    def test_stage_counts_decrease_on_table_overgrouping_fixture(self):
        fixture = _load("fake_one_group_per_table_cell")

        stop_set = build_normalized_stop_set(
            build_stop_association_result(stop_groups=fixture["stop_groups"]),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(stop_set["raw_stop_signal_count"], 3)
        self.assertEqual(stop_set["premerge_group_count"], 3)
        self.assertEqual(stop_set["post_row_merge_group_count"], 1)
        self.assertEqual(stop_set["post_section_merge_group_count"], 1)
        self.assertEqual(stop_set["post_noise_filter_group_count"], 1)
        self.assertEqual(stop_set["post_dedupe_group_count"], 1)
        self.assertEqual(len(stop_set["stops"]), 1)

    def test_stage_counts_decrease_on_section_line_fixture(self):
        fixture = _load("fake_one_group_per_line_cluster")

        stop_set = build_normalized_stop_set(
            build_stop_association_result(stop_groups=fixture["stop_groups"]),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(stop_set["raw_stop_signal_count"], 3)
        self.assertEqual(stop_set["premerge_group_count"], 3)
        self.assertEqual(stop_set["post_row_merge_group_count"], 3)
        self.assertEqual(stop_set["post_section_merge_group_count"], 1)
        self.assertEqual(stop_set["post_dedupe_group_count"], 1)

    def test_clean_simple_stops_are_not_lost(self):
        fixture = _load("fake_date_time_split_from_location_by_row")

        stop_set = build_normalized_stop_set(
            build_stop_association_result(stop_groups=fixture["stop_groups"]),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(stop_set["raw_stop_signal_count"], 2)
        self.assertEqual(stop_set["post_dedupe_group_count"], 1)
        self.assertEqual(stop_set["pickup_count"], 1)


if __name__ == "__main__":
    unittest.main()
