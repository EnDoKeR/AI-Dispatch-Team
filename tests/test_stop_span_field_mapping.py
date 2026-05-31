import json
import unittest
from pathlib import Path

from app.document_ai.private_measurement import (
    FIELD_STATUS_CONFLICT,
    FIELD_STATUS_MISSING,
    FIELD_STATUS_RESOLVED,
    build_field_status_summary,
)
from app.document_ai.private_measurement_pipeline import (
    _merge_stop_span_flat_fields_into_field_statuses,
)


FIXTURE_DIR = (
    Path(__file__).parent
    / "fixtures"
    / "document_ai"
    / "core_field_hardening"
    / "stop_span_field_mapping"
)


def _load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _initial_statuses(payload):
    return [
        build_field_status_summary(
            field_name=row["field_name"],
            status=row["status"],
        )
        for row in payload.get("initial_field_statuses", [])
    ]


def _status_map(statuses):
    return {row["field_name"]: row for row in statuses}


class StopSpanFieldMappingTests(unittest.TestCase):
    def test_span_resolved_fields_fill_missing_core_field_statuses(self):
        payload = _load_fixture("fake_span_pickup_delivery_fields_not_mapped.json")

        statuses = _merge_stop_span_flat_fields_into_field_statuses(
            _initial_statuses(payload),
            payload["span_normalized_stop_set"],
        )
        mapped = _status_map(statuses)

        for field_name in payload["expected_resolved_fields"]:
            with self.subTest(field_name=field_name):
                self.assertEqual(mapped[field_name]["status"], FIELD_STATUS_RESOLVED)
                self.assertEqual(mapped[field_name]["candidate_count"], 1)
                self.assertTrue(mapped[field_name]["selected_candidate_present"])
                self.assertIn("mapped_from_stop_span", mapped[field_name]["warning_codes"])

    def test_span_mapping_preserves_existing_conflict_status(self):
        payload = _load_fixture("fake_span_mapping_preserves_conflict.json")

        statuses = _merge_stop_span_flat_fields_into_field_statuses(
            _initial_statuses(payload),
            payload["span_normalized_stop_set"],
        )
        mapped = _status_map(statuses)

        self.assertEqual(mapped["pickup_location"]["status"], FIELD_STATUS_CONFLICT)
        self.assertEqual(mapped["pickup_date"]["status"], FIELD_STATUS_RESOLVED)

    def test_span_missing_fields_do_not_invent_core_field_values(self):
        payload = _load_fixture("fake_span_missing_fields_not_invented.json")

        statuses = _merge_stop_span_flat_fields_into_field_statuses(
            _initial_statuses(payload),
            payload["span_normalized_stop_set"],
        )
        mapped = _status_map(statuses)

        for field_name in payload["expected_unresolved_fields"]:
            with self.subTest(field_name=field_name):
                self.assertEqual(mapped[field_name]["status"], FIELD_STATUS_MISSING)

    def test_serialized_mapping_statuses_do_not_include_private_values(self):
        payload = _load_fixture("fake_span_pickup_delivery_fields_not_mapped.json")

        statuses = _merge_stop_span_flat_fields_into_field_statuses(
            _initial_statuses(payload),
            payload["span_normalized_stop_set"],
        )
        serialized = json.dumps(statuses)

        self.assertNotIn("Predicted Value", serialized)
        self.assertNotIn("Fake Broker", serialized)
        self.assertNotIn("private_key", serialized)


if __name__ == "__main__":
    unittest.main()
