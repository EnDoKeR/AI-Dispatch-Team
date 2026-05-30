import json
import unittest
from pathlib import Path

from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_LOCATION,
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    NORMALIZED_STOP_FIELD_TIME,
)
from app.document_ai.stop_association import build_stop_association_result
from app.document_ai.stop_normalization import (
    WARNING_SECTION_CONTEXT_GROUPS_MERGED,
    WARNING_TABLE_ROW_GROUPS_MERGED,
    build_normalized_stop_set,
    merge_stop_groups_by_section_context,
    merge_stop_groups_by_table_row,
)


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "stop_normalization"
)
CALIBRATION_DIR = FIXTURE_DIR / "calibration_patterns"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _field_status(stop, field_name):
    for field in stop.get("fields", []) or []:
        if field.get("field_name") == field_name:
            return field.get("status")
    return ""


class StopTableRowMergeTests(unittest.TestCase):
    def test_one_stop_per_cell_bug_collapses_to_one_stop_per_row(self):
        fixture = _load(CALIBRATION_DIR / "fake_one_stop_per_cell_bug.json")

        stop_set = build_normalized_stop_set(
            build_stop_association_result(stop_groups=fixture["stop_groups"]),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(stop_set["raw_stop_group_count"], 3)
        self.assertEqual(len(stop_set["stops"]), 1)
        self.assertEqual(stop_set["table_row_merge_count"], 2)
        self.assertIn(WARNING_TABLE_ROW_GROUPS_MERGED, stop_set["warning_codes"])

    def test_table_pickup_and_delivery_rows_remain_two_stops(self):
        fixture = _load(FIXTURE_DIR / "fake_table_pickup_delivery_groups.json")

        stop_set = build_normalized_stop_set(
            build_stop_association_result(stop_groups=fixture["stop_groups"]),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(len(stop_set["stops"]), 2)
        self.assertEqual(stop_set["pickup_count"], 1)
        self.assertEqual(stop_set["delivery_count"], 1)

    def test_multi_stop_table_preserves_row_count(self):
        fixture = _load(FIXTURE_DIR / "fake_multi_stop_three_rows.json")

        stop_set = build_normalized_stop_set(
            build_stop_association_result(stop_groups=fixture["stop_groups"]),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(len(stop_set["stops"]), 3)

    def test_date_time_location_remain_attached_after_row_merge(self):
        fixture = _load(CALIBRATION_DIR / "fake_table_cell_over_grouping.json")

        stop_set = build_normalized_stop_set(
            build_stop_association_result(stop_groups=fixture["stop_groups"]),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )
        stop = stop_set["stops"][0]

        self.assertEqual(
            _field_status(stop, NORMALIZED_STOP_FIELD_LOCATION),
            NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
        )
        self.assertEqual(
            _field_status(stop, NORMALIZED_STOP_FIELD_DATE),
            NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
        )
        self.assertEqual(
            _field_status(stop, NORMALIZED_STOP_FIELD_TIME),
            NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
        )

    def test_merge_helper_keeps_non_table_groups_passthrough(self):
        fixture = _load(CALIBRATION_DIR / "fake_date_time_split_from_location.json")

        result = merge_stop_groups_by_table_row(fixture["stop_groups"])

        self.assertEqual(result["merge_count"], 0)
        self.assertEqual(len(result["merged_groups"]), 2)

    def test_split_section_location_and_datetime_merge_to_one_stop(self):
        fixture = _load(CALIBRATION_DIR / "fake_date_time_split_from_location.json")

        stop_set = build_normalized_stop_set(
            build_stop_association_result(stop_groups=fixture["stop_groups"]),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )
        stop = stop_set["stops"][0]

        self.assertEqual(len(stop_set["stops"]), 1)
        self.assertEqual(stop_set["section_context_merge_count"], 1)
        self.assertIn(WARNING_SECTION_CONTEXT_GROUPS_MERGED, stop_set["warning_codes"])
        self.assertEqual(
            _field_status(stop, NORMALIZED_STOP_FIELD_LOCATION),
            NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
        )
        self.assertEqual(
            _field_status(stop, NORMALIZED_STOP_FIELD_DATE),
            NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
        )
        self.assertEqual(
            _field_status(stop, NORMALIZED_STOP_FIELD_TIME),
            NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
        )

    def test_section_merge_helper_keeps_distinct_stop_types_separate(self):
        fixture = _load(FIXTURE_DIR / "fake_table_pickup_delivery_groups.json")

        result = merge_stop_groups_by_section_context(fixture["stop_groups"])

        self.assertEqual(result["merge_count"], 0)
        self.assertEqual(len(result["merged_groups"]), 2)


if __name__ == "__main__":
    unittest.main()
