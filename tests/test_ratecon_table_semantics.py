import unittest

from app.document_ai.ratecon_table_semantics import (
    ROLE_DATE,
    ROLE_LOAD_IDENTITY,
    ROLE_LOCATION,
    ROLE_RATE,
    ROLE_REFERENCE,
    ROLE_STOP_ROLE,
    ROLE_TIME,
    classify_cell_semantic_role,
    classify_table_semantics,
    safe_value_shape,
)


class RateConTableSemanticsTests(unittest.TestCase):
    def test_recognizes_stop_location_date_time_headers(self):
        table = {
            "rows": [
                {
                    "row_index": 0,
                    "cells": [
                        {"text": "Stop", "column_index": 0},
                        {"text": "Location", "column_index": 1},
                        {"text": "Date", "column_index": 2},
                        {"text": "Time", "column_index": 3},
                    ],
                }
            ]
        }

        result = classify_table_semantics(table)

        self.assertEqual(result["recognized_kind"], "stop")
        self.assertEqual(result["header_roles"]["0"], ROLE_STOP_ROLE)
        self.assertEqual(result["header_roles"]["1"], ROLE_LOCATION)
        self.assertEqual(result["header_roles"]["2"], ROLE_DATE)
        self.assertEqual(result["header_roles"]["3"], ROLE_TIME)

    def test_recognizes_load_and_rate_headers(self):
        self.assertEqual(classify_cell_semantic_role("Load #"), ROLE_LOAD_IDENTITY)
        self.assertEqual(classify_cell_semantic_role("Rate Confirmation #"), ROLE_LOAD_IDENTITY)
        self.assertEqual(classify_cell_semantic_role("Carrier Pay"), ROLE_RATE)

    def test_reference_header_is_not_strong_load(self):
        self.assertEqual(classify_cell_semantic_role("PO #"), ROLE_REFERENCE)
        self.assertEqual(classify_cell_semantic_role("BOL"), ROLE_REFERENCE)

    def test_header_row_can_be_second_row(self):
        table = {
            "rows": [
                {"row_index": 0, "cells": [{"text": "Schedule", "column_index": 0}]},
                {
                    "row_index": 1,
                    "cells": [
                        {"text": "Pickup Location", "column_index": 0},
                        {"text": "Pickup Date", "column_index": 1},
                    ],
                },
            ]
        }

        result = classify_table_semantics(table)

        self.assertEqual(result["header_row_index"], 1)
        self.assertIn("0", result["header_roles"])
        self.assertIn("1", result["header_roles"])

    def test_safe_value_shape_does_not_expose_value(self):
        shape = safe_value_shape("ABC-123")

        self.assertEqual(shape["length"], 7)
        self.assertTrue(shape["has_digits"])
        self.assertTrue(shape["has_letters"])
        self.assertNotIn("ABC-123", shape.values())


if __name__ == "__main__":
    unittest.main()
