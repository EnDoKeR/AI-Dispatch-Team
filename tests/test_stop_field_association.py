import json
import unittest
from pathlib import Path

from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_LOCATION,
    NORMALIZED_STOP_FIELD_REFERENCE,
    NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
    NORMALIZED_STOP_FIELD_STATUS_MISSING,
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    NORMALIZED_STOP_FIELD_TIME,
)
from app.document_ai.stop_association import (
    STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
    STOP_FIELD_DATE,
    STOP_FIELD_LOCATION,
    STOP_TYPE_PICKUP,
    build_stop_field_candidate,
    build_stop_group_candidate,
)
from app.document_ai.stop_normalization import (
    FIELD_WARNING_CONFLICT,
    associate_stop_fields,
    build_normalized_stop_from_group,
    compute_stop_completeness,
    resolve_stop_field,
)


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "stop_normalization"
)


def load_fixture(name):
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _field_status(stop, field_name):
    fields = {
        field["field_name"]: field
        for field in stop["fields"]
    }
    return fields[field_name]["status"]


class StopFieldAssociationTests(unittest.TestCase):
    def test_clean_table_row_resolves_location_date_time(self):
        fixture = load_fixture("fake_table_pickup_delivery_groups")
        stop = build_normalized_stop_from_group(fixture["stop_groups"][0])

        self.assertEqual(_field_status(stop, NORMALIZED_STOP_FIELD_LOCATION), NORMALIZED_STOP_FIELD_STATUS_RESOLVED)
        self.assertEqual(_field_status(stop, NORMALIZED_STOP_FIELD_DATE), NORMALIZED_STOP_FIELD_STATUS_RESOLVED)
        self.assertEqual(_field_status(stop, NORMALIZED_STOP_FIELD_TIME), NORMALIZED_STOP_FIELD_STATUS_RESOLVED)

    def test_missing_date_stays_missing(self):
        fixture = load_fixture("fake_location_without_date")
        stop = build_normalized_stop_from_group(fixture["stop_groups"][0])
        completeness = compute_stop_completeness(stop)

        self.assertEqual(_field_status(stop, NORMALIZED_STOP_FIELD_DATE), NORMALIZED_STOP_FIELD_STATUS_MISSING)
        self.assertIn(NORMALIZED_STOP_FIELD_DATE, completeness["missing_required_fields"])

    def test_conflicting_date_marks_conflict(self):
        first = build_stop_field_candidate(
            "group_conflict",
            field_name=STOP_FIELD_DATE,
            candidate_id="date_candidate_1",
            confidence=0.9,
        )
        second = build_stop_field_candidate(
            "group_conflict",
            field_name=STOP_FIELD_DATE,
            candidate_id="date_candidate_2",
            confidence=0.9,
        )

        field = resolve_stop_field(NORMALIZED_STOP_FIELD_DATE, [first, second])

        self.assertEqual(field["status"], NORMALIZED_STOP_FIELD_STATUS_CONFLICT)
        self.assertIn(FIELD_WARNING_CONFLICT, field["warning_codes"])

    def test_nearby_header_date_not_used_as_stop_date(self):
        stop_group = build_stop_group_candidate(
            "pickup_group",
            stop_type=STOP_TYPE_PICKUP,
            source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
            section_role="PICKUP_SECTION",
            field_candidates=[
                build_stop_field_candidate(
                    "pickup_group",
                    field_name=STOP_FIELD_LOCATION,
                    candidate_id="pickup_location",
                    confidence=0.9,
                )
            ],
        )
        header_group = build_stop_group_candidate(
            "header_date",
            source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
            section_role="HEADER",
            field_candidates=[
                build_stop_field_candidate(
                    "header_date",
                    field_name=STOP_FIELD_DATE,
                    candidate_id="header_date_candidate",
                    confidence=0.9,
                )
            ],
        )

        stop = build_normalized_stop_from_group(stop_group)
        header_fields = associate_stop_fields(header_group)

        self.assertEqual(_field_status(stop, NORMALIZED_STOP_FIELD_DATE), NORMALIZED_STOP_FIELD_STATUS_MISSING)
        self.assertIn(NORMALIZED_STOP_FIELD_DATE, header_fields)

    def test_reference_attaches_to_correct_stop(self):
        fixture = load_fixture("fake_pu_so_continuation_groups")
        stop = build_normalized_stop_from_group(fixture["stop_groups"][0])
        fields = {field["field_name"]: field for field in stop["fields"]}

        self.assertEqual(fields[NORMALIZED_STOP_FIELD_REFERENCE]["status"], NORMALIZED_STOP_FIELD_STATUS_RESOLVED)

    def test_multi_stop_fields_preserved(self):
        fixture = load_fixture("fake_multi_stop_three_rows")
        stops = [build_normalized_stop_from_group(group) for group in fixture["stop_groups"]]

        self.assertEqual(len(stops), 3)
        self.assertEqual(
            [stop["source_group_ids"][0] for stop in stops],
            ["group_stop_1", "group_stop_2", "group_stop_3"],
        )


if __name__ == "__main__":
    unittest.main()
