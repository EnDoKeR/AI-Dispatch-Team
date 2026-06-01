import unittest

from app.document_ai.structured_stop_values import (
    STOP_STATUS_COMPLETE,
    STOP_STATUS_EMPTY,
    STOP_STATUS_UNSUPPORTED,
    STOP_STATUS_USEFUL_PARTIAL,
    normalize_stop_candidate_value,
    safe_stop_normalization_summary,
    stop_conflict_types,
)


class StructuredStopValueTests(unittest.TestCase):
    def test_dict_stop_value_normalizes_complete(self):
        normalized = normalize_stop_candidate_value(
            {
                "role": "pickup",
                "facility": "Fake Facility",
                "date": "01/02/2030",
                "time": "08:00",
                "metadata": {"page_span": [1]},
            },
            "pickup_stops",
            {"structured_stop_candidate": True},
        )

        self.assertEqual(normalized["structure_status"], STOP_STATUS_COMPLETE)
        self.assertTrue(normalized["has_location"])
        self.assertTrue(normalized["has_date"])
        self.assertTrue(normalized["has_time"])
        self.assertGreaterEqual(normalized["completeness_score"], 0.85)

    def test_list_stop_value_normalizes_useful_partial(self):
        normalized = normalize_stop_candidate_value(
            [{"role": "delivery", "city": "Fake City"}],
            "delivery_stops",
            {"structured_stop_candidate": True},
        )

        self.assertEqual(normalized["structure_status"], STOP_STATUS_USEFUL_PARTIAL)
        self.assertTrue(normalized["has_location"])
        self.assertFalse(normalized["has_date"])

    def test_metadata_backed_table_stop_preserves_refs(self):
        normalized = normalize_stop_candidate_value(
            "pickup_layout_stop_present",
            "pickup_stops",
            {
                "structured_stop_candidate": True,
                "stop_role": "pickup",
                "has_location": True,
                "has_date": True,
                "table_index": 2,
                "row_index": 4,
                "cell_indices": [1, 2],
            },
        )

        self.assertEqual(normalized["structure_status"], STOP_STATUS_COMPLETE)
        self.assertEqual(normalized["stops"][0]["table_refs"][0]["table_index"], 2)

    def test_malformed_object_is_unsupported_not_blank(self):
        normalized = normalize_stop_candidate_value(
            [object()],
            "pickup_stops",
            {"structured_stop_candidate": True},
        )

        self.assertEqual(normalized["structure_status"], STOP_STATUS_UNSUPPORTED)
        self.assertIn("unsupported", normalized["normalization_warnings"])

    def test_empty_string_or_list_is_empty(self):
        self.assertEqual(
            normalize_stop_candidate_value("", "pickup_stops")["structure_status"],
            STOP_STATUS_EMPTY,
        )
        self.assertEqual(
            normalize_stop_candidate_value([], "pickup_stops")["structure_status"],
            STOP_STATUS_EMPTY,
        )

    def test_conflict_types_are_safe_and_specific(self):
        left = normalize_stop_candidate_value(
            {"role": "pickup", "city": "Fake A", "date": "01/02/2030"},
            "pickup_stops",
            {"structured_stop_candidate": True},
        )
        right = normalize_stop_candidate_value(
            {"role": "pickup", "city": "Fake B", "date": "01/03/2030"},
            "pickup_stops",
            {"structured_stop_candidate": True},
        )

        conflicts = stop_conflict_types(left, right)

        self.assertIn("location_conflict", conflicts)
        self.assertIn("date_conflict", conflicts)

    def test_safe_summary_excludes_raw_stop_values(self):
        normalized = normalize_stop_candidate_value(
            {"role": "pickup", "facility": "Private Facility", "date": "01/02/2030"},
            "pickup_stops",
            {"structured_stop_candidate": True},
        )

        summary_text = str(safe_stop_normalization_summary(normalized))

        self.assertNotIn("Private Facility", summary_text)
        self.assertIn("has_location", summary_text)


if __name__ == "__main__":
    unittest.main()
