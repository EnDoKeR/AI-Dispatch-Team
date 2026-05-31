import json
import unittest
from pathlib import Path

from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_LOCATION,
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    NORMALIZED_STOP_FIELD_TIME,
)
from app.document_ai.stop_association import (
    build_stop_association_result,
    build_stop_groups_from_layout_sections,
)
from app.document_ai.stop_normalization import (
    build_normalized_stop_set,
    merge_stop_groups_by_table_row,
)


PROVENANCE_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "document_ai" / "stop_provenance"
)


def _load(name):
    return json.loads((PROVENANCE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _field_status(stop, field_name):
    for field in stop.get("fields", []) or []:
        if field.get("field_name") == field_name:
            return field.get("status")
    return ""


class StopDateTimeMergeTests(unittest.TestCase):
    def test_date_time_cells_attach_after_table_row_merge(self):
        fixture = _load("fake_date_time_split_from_location_by_row")

        stop_set = build_normalized_stop_set(
            build_stop_association_result(stop_groups=fixture["stop_groups"]),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(len(stop_set["stops"]), 1)
        self.assertEqual(stop_set["table_row_merge_count"], 1)
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

    def test_merged_table_field_candidates_point_to_merged_group(self):
        fixture = _load("fake_date_time_split_from_location_by_row")

        result = merge_stop_groups_by_table_row(fixture["stop_groups"])
        group = result["merged_groups"][0]

        self.assertEqual(result["merge_count"], 1)
        self.assertTrue(
            all(
                candidate.get("stop_group_id") == group["stop_group_id"]
                for candidate in group["field_candidates"]
            )
        )

    def test_date_time_lines_attach_after_line_cluster_merge(self):
        artifact = {
            "pages": [
                {
                    "page_number": 1,
                    "lines": [
                        {
                            "line_id": "line_1",
                            "text_redacted": "PU FAKE ORIGIN",
                            "page_number": 1,
                        },
                        {
                            "line_id": "line_2",
                            "text_redacted": "PU Date <DATE>",
                            "page_number": 1,
                        },
                        {
                            "line_id": "line_3",
                            "text_redacted": "PU Appt <TIME>",
                            "page_number": 1,
                        },
                    ],
                    "blocks": [],
                }
            ]
        }

        association = build_stop_groups_from_layout_sections(artifact)
        stop_set = build_normalized_stop_set(
            association,
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(len(association["stop_groups"]), 1)
        self.assertEqual(len(stop_set["stops"]), 1)
        stop = stop_set["stops"][0]
        self.assertEqual(
            _field_status(stop, NORMALIZED_STOP_FIELD_DATE),
            NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
        )
        self.assertEqual(
            _field_status(stop, NORMALIZED_STOP_FIELD_TIME),
            NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
        )


if __name__ == "__main__":
    unittest.main()
