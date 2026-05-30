import json
import unittest
from pathlib import Path

from app.document_ai.stop_association import (
    STOP_FIELD_DATE,
    STOP_FIELD_LOCATION,
    STOP_FIELD_REFERENCE,
    STOP_FIELD_TIME,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_PICKUP,
    build_stop_groups_from_layout_tables,
    classify_stop_row,
    detect_stop_table_columns,
)


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_association")


def _load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class StopTableAssociationTests(unittest.TestCase):
    def test_detects_stop_table_columns(self):
        artifact = _load_fixture("fake_layout_table_stop_rows.json")
        table = artifact["pages"][0]["tables"][0]

        columns = detect_stop_table_columns(table)

        self.assertIn(STOP_FIELD_LOCATION, columns.values())
        self.assertIn(STOP_FIELD_DATE, columns.values())
        self.assertIn(STOP_FIELD_TIME, columns.values())
        self.assertIn(STOP_FIELD_REFERENCE, columns.values())

    def test_pickup_delivery_rows_preserve_field_association(self):
        artifact = _load_fixture("fake_layout_table_stop_rows.json")

        result = build_stop_groups_from_layout_tables(artifact)

        self.assertEqual(len(result["stop_groups"]), 2)
        self.assertEqual(result["stop_groups"][0]["stop_type"], STOP_TYPE_PICKUP)
        self.assertEqual(result["stop_groups"][1]["stop_type"], STOP_TYPE_DELIVERY)
        first_fields = {
            candidate["field_name"]
            for candidate in result["stop_groups"][0]["field_candidates"]
        }
        self.assertEqual(
            first_fields,
            {STOP_FIELD_LOCATION, STOP_FIELD_DATE, STOP_FIELD_TIME, STOP_FIELD_REFERENCE},
        )

    def test_multi_stop_table_rows_are_not_collapsed(self):
        artifact = _load_fixture("fake_layout_multi_stop_order.json")

        result = build_stop_groups_from_layout_tables(artifact)

        self.assertEqual(len(result["stop_groups"]), 3)
        self.assertEqual(
            [group["stop_sequence"] for group in result["stop_groups"]],
            [1, 2, 3],
        )

    def test_missing_date_is_not_invented(self):
        artifact = _load_fixture("fake_layout_strong_layout_weak_text.json")

        result = build_stop_groups_from_layout_tables(artifact)

        fields = {
            candidate["field_name"]
            for group in result["stop_groups"]
            for candidate in group["field_candidates"]
        }
        self.assertIn(STOP_FIELD_DATE, fields)
        self.assertNotIn("delivery_date", fields)

    def test_ambiguous_stop_type_gets_warning(self):
        row = {
            0: {"text_redacted": "3"},
            1: {"text_redacted": "Appointment"},
            2: {"text_redacted": "FAKE STOP"},
        }
        columns = {0: "sequence", 1: "type", 2: STOP_FIELD_LOCATION}

        classification = classify_stop_row(row, columns)

        self.assertEqual(classification["stop_type"], "stop")
        self.assertIn("ambiguous_stop_type", classification["warning_codes"])

    def test_provider_style_table_rows_produce_stop_groups_without_type_column(self):
        artifact = {
            "pages": [
                {
                    "page_number": 1,
                    "tables": [
                        {
                            "table_id": "P1_T1",
                            "page_number": 1,
                            "header_rows": [0],
                            "cells": [
                                {"row_index": 0, "col_index": 0, "text_redacted": "Stop"},
                                {"row_index": 0, "col_index": 1, "text_redacted": "Location"},
                                {"row_index": 0, "col_index": 2, "text_redacted": "Date"},
                                {"row_index": 0, "col_index": 3, "text_redacted": "Time"},
                                {"row_index": 1, "col_index": 0, "text_redacted": "PU"},
                                {"row_index": 1, "col_index": 1, "text_redacted": "FAKE ORIGIN"},
                                {"row_index": 1, "col_index": 2, "text_redacted": "<DATE>"},
                                {"row_index": 1, "col_index": 3, "text_redacted": "<TIME>"},
                                {"row_index": 2, "col_index": 0, "text_redacted": "SO"},
                                {"row_index": 2, "col_index": 1, "text_redacted": "FAKE DEST"},
                                {"row_index": 2, "col_index": 2, "text_redacted": "<DATE>"},
                                {"row_index": 2, "col_index": 3, "text_redacted": "<TIME>"},
                            ],
                        }
                    ],
                }
            ]
        }

        result = build_stop_groups_from_layout_tables(artifact)

        self.assertEqual(len(result["stop_groups"]), 2)
        self.assertEqual(result["stop_groups"][0]["stop_type"], STOP_TYPE_PICKUP)
        self.assertEqual(result["stop_groups"][1]["stop_type"], STOP_TYPE_DELIVERY)

    def test_provider_style_table_with_weak_headers_still_preserves_rows(self):
        artifact = {
            "pages": [
                {
                    "page_number": 1,
                    "tables": [
                        {
                            "table_id": "P1_T1",
                            "page_number": 1,
                            "header_rows": [0],
                            "cells": [
                                {"row_index": 0, "col_index": 0, "text_redacted": "#"},
                                {"row_index": 0, "col_index": 1, "text_redacted": "City/State"},
                                {"row_index": 0, "col_index": 2, "text_redacted": "Appt"},
                                {"row_index": 1, "col_index": 0, "text_redacted": "Stop 1 Pickup"},
                                {"row_index": 1, "col_index": 1, "text_redacted": "FAKE ORIGIN"},
                                {"row_index": 1, "col_index": 2, "text_redacted": "<TIME>"},
                            ],
                        }
                    ],
                }
            ]
        }

        result = build_stop_groups_from_layout_tables(artifact)

        self.assertEqual(len(result["stop_groups"]), 1)
        self.assertEqual(result["stop_groups"][0]["stop_type"], STOP_TYPE_PICKUP)

    def test_date_and_time_signals_in_unlabeled_row_cells_attach_to_row(self):
        artifact = {
            "pages": [
                {
                    "page_number": 1,
                    "tables": [
                        {
                            "table_id": "P1_T1",
                            "page_number": 1,
                            "header_rows": [0],
                            "cells": [
                                {"row_index": 0, "col_index": 0, "text_redacted": "Stop"},
                                {"row_index": 0, "col_index": 1, "text_redacted": "Location"},
                                {"row_index": 0, "col_index": 2, "text_redacted": "Notes"},
                                {"row_index": 1, "col_index": 0, "text_redacted": "Pickup"},
                                {"row_index": 1, "col_index": 1, "text_redacted": "FAKE ORIGIN"},
                                {"row_index": 1, "col_index": 2, "text_redacted": "Appt 02/01/2099 07:30-10:00"},
                            ],
                        }
                    ],
                }
            ]
        }

        result = build_stop_groups_from_layout_tables(artifact)
        fields = {
            candidate["field_name"]
            for group in result["stop_groups"]
            for candidate in group["field_candidates"]
        }

        self.assertIn(STOP_FIELD_LOCATION, fields)
        self.assertIn(STOP_FIELD_DATE, fields)
        self.assertIn(STOP_FIELD_TIME, fields)


if __name__ == "__main__":
    unittest.main()
