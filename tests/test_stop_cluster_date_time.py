import json
import unittest
from pathlib import Path

from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
    NORMALIZED_STOP_FIELD_STATUS_MISSING,
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    NORMALIZED_STOP_FIELD_TIME,
)
from app.document_ai.stop_association import build_stop_association_result
from app.document_ai.stop_normalization import build_normalized_stop_set


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "stop_pipeline_wiring"
)


def _stop_set_from_groups(groups):
    return build_normalized_stop_set(
        build_stop_association_result(stop_groups=groups),
        classification_result={
            "document_alias": "RATECON_FAKE",
            "normal_load_movement": True,
        },
    )


def _field_status(stop, field_name):
    for field in stop.get("fields", []):
        if field.get("field_name") == field_name:
            return field.get("status")
    return ""


class StopClusterDateTimeTests(unittest.TestCase):
    def test_date_and_time_lines_attach_to_cluster(self):
        fixture = json.loads(
            (FIXTURE_DIR / "fake_mergeable_single_line_stop_section.json").read_text(
                encoding="utf-8"
            )
        )

        stop_set = _stop_set_from_groups(fixture["stop_groups"])
        stop = stop_set["stops"][0]

        self.assertEqual(_field_status(stop, NORMALIZED_STOP_FIELD_DATE), NORMALIZED_STOP_FIELD_STATUS_RESOLVED)
        self.assertEqual(_field_status(stop, NORMALIZED_STOP_FIELD_TIME), NORMALIZED_STOP_FIELD_STATUS_RESOLVED)
        self.assertEqual(stop_set["single_line_cluster_merge_count"], 7)

    def test_conflicting_dates_mark_conflict(self):
        fixture = json.loads(
            (FIXTURE_DIR / "fake_passthrough_should_fail.json").read_text(
                encoding="utf-8"
            )
        )
        groups = list(fixture["stop_groups"])
        duplicate_date = dict(groups[1])
        duplicate_date["stop_group_id"] = "line_c"
        duplicate_date["field_candidates"] = [
            dict(duplicate_date["field_candidates"][0], candidate_id="line_c_date")
        ]
        groups.append(duplicate_date)

        stop_set = _stop_set_from_groups(groups)

        self.assertEqual(
            _field_status(stop_set["stops"][0], NORMALIZED_STOP_FIELD_DATE),
            NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
        )

    def test_missing_date_remains_missing(self):
        fixture = json.loads(
            (FIXTURE_DIR / "fake_non_mergeable_distinct_stops.json").read_text(
                encoding="utf-8"
            )
        )

        stop_set = _stop_set_from_groups([fixture["stop_groups"][0]])

        self.assertEqual(
            _field_status(stop_set["stops"][0], NORMALIZED_STOP_FIELD_DATE),
            NORMALIZED_STOP_FIELD_STATUS_MISSING,
        )


if __name__ == "__main__":
    unittest.main()
