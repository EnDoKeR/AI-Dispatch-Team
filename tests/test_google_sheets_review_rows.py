import unittest

from app.integrations.google_sheets_review import (
    REVIEW_SYNC_WARNING,
    SYNC_MODE_PRIVATE_VALUES_TEST_ONLY,
    SYNC_MODE_STATUS_ONLY,
    build_google_review_tab_rows,
)


def _fake_stop_set():
    return {
        "stops": [
            {
                "stop_id": "span_stop_001",
                "sequence": 1,
                "stop_type": "pickup",
                "review_required": True,
                "fields": [
                    {
                        "field_name": "location",
                        "status": "resolved",
                        "confidence": "high",
                        "selected_value": "Fake Private Stop Value",
                        "evidence_refs": [
                            {"evidence_type": "layout_line", "page_number": 1}
                        ],
                    }
                ],
            }
        ],
        "pickup_count": 1,
        "delivery_count": 0,
        "stop_count": 0,
        "unknown_count": 0,
    }


def _fake_measurement_row():
    return {
        "document_alias": "RATECON_001",
        "document_type": "LOAD_CONFIRMATION",
        "classification_status": "classified",
        "extraction_relevant": True,
        "normal_load_movement": True,
        "extraction_status": "TEXT_EXTRACTED",
        "layout_provider_status": "success",
        "old_raw_stop_groups": 8,
        "old_normalized_stops": 8,
        "span_anchor_count": 2,
        "stop_span_count": 2,
        "span_normalized_stop_count": 2,
        "span_pickup_count": 1,
        "span_delivery_count": 0,
        "span_generic_stop_count": 1,
        "span_unknown_count": 0,
        "span_date_resolved_count": 1,
        "span_date_missing_count": 1,
        "span_time_resolved_count": 0,
        "span_time_missing_count": 2,
        "span_review_required_count": 1,
        "span_normalized_stop_set": _fake_stop_set(),
        "field_statuses": [
            {
                "field_name": "rate",
                "status": "resolved",
                "confidence": "high",
                "selected_value": "Fake Private Rate Value",
                "evidence_type": "layout_table",
            },
            {"field_name": "load_number", "status": "resolved"},
            {"field_name": "broker_name", "status": "needs_review"},
            {"field_name": "pickup_location", "status": "resolved"},
            {"field_name": "pickup_date", "status": "needs_review"},
            {"field_name": "delivery_location", "status": "resolved"},
            {"field_name": "delivery_date", "status": "resolved"},
        ],
        "blocker_categories": ["VALUE_REVIEW_NEEDED"],
    }


def _flatten(rows_by_tab):
    return "\n".join(
        str(cell)
        for rows in rows_by_tab.values()
        for row in rows
        for cell in row
    )


class GoogleSheetsReviewRowsTests(unittest.TestCase):
    def test_builds_expected_review_tabs(self):
        rows_by_tab = build_google_review_tab_rows([_fake_measurement_row()])

        self.assertEqual(
            set(rows_by_tab),
            {
                "RC_Document_Summary",
                "RC_Stop_Review",
                "RC_Field_Review",
                "RC_Rate_Review",
                "RC_Instructions",
                "RC_Feedback_Summary",
            },
        )
        self.assertEqual(rows_by_tab["RC_Document_Summary"][0][0], REVIEW_SYNC_WARNING)
        self.assertIn("Measurement Alias", rows_by_tab["RC_Document_Summary"][1])

    def test_status_only_mode_excludes_private_values(self):
        rows_by_tab = build_google_review_tab_rows(
            [_fake_measurement_row()],
            sync_mode=SYNC_MODE_STATUS_ONLY,
            include_private_values=True,
        )

        payload = _flatten(rows_by_tab)
        self.assertNotIn("Fake Private Stop Value", payload)
        self.assertNotIn("Fake Private Rate Value", payload)

    def test_private_test_mode_includes_values_only_when_explicit(self):
        rows_by_tab = build_google_review_tab_rows(
            [_fake_measurement_row()],
            sync_mode=SYNC_MODE_PRIVATE_VALUES_TEST_ONLY,
            include_private_values=True,
        )

        payload = _flatten(rows_by_tab)
        self.assertIn("Fake Private Stop Value", payload)
        self.assertIn("Fake Private Rate Value", payload)

    def test_private_test_mode_still_redacts_without_explicit_flag(self):
        rows_by_tab = build_google_review_tab_rows(
            [_fake_measurement_row()],
            sync_mode=SYNC_MODE_PRIVATE_VALUES_TEST_ONLY,
            include_private_values=False,
        )

        self.assertNotIn("Fake Private Stop Value", _flatten(rows_by_tab))

    def test_headers_include_review_columns_and_generic_stop_count(self):
        rows_by_tab = build_google_review_tab_rows([_fake_measurement_row()])

        document_headers = rows_by_tab["RC_Document_Summary"][1]
        stop_headers = rows_by_tab["RC_Stop_Review"][1]
        self.assertIn("Generic Stop Count", document_headers)
        self.assertIn("User Correct? yes/no/unknown", stop_headers)
        self.assertIn("User Expected Value LOCAL ONLY", stop_headers)


if __name__ == "__main__":
    unittest.main()
