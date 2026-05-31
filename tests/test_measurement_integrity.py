import json
import unittest

from app.document_ai.measurement_integrity import (
    ISSUE_FIELD_STATUS_DENOMINATOR_MISMATCH,
    ISSUE_NEGATIVE_COUNT,
    ISSUE_OCR_DOC_COUNTED_AS_NORMAL_FAILURE,
    ISSUE_SPAN_FIELD_STATUS_DENOMINATOR_MISMATCH,
    ISSUE_SPAN_TYPE_COUNT_MISMATCH,
    ISSUE_STOP_TYPE_COUNT_MISMATCH,
    check_measurement_aggregate_integrity,
    check_measurement_row_integrity,
    summarize_integrity_issues,
)


def _issue_codes(issues):
    return {issue["issue_code"] for issue in issues}


class MeasurementIntegrityTests(unittest.TestCase):
    def test_detects_stop_type_count_mismatch(self):
        issues = check_measurement_row_integrity(
            {
                "document_alias": "RATECON_001",
                "normalized_stop_count": 3,
                "pickup_count": 1,
                "delivery_count": 1,
                "unknown_stop_count": 0,
            }
        )

        self.assertIn(ISSUE_STOP_TYPE_COUNT_MISMATCH, _issue_codes(issues))
        self.assertEqual(issues[0]["alias"], "RATECON_001")
        self.assertTrue(issues[0]["private_values_redacted"])

    def test_detects_span_type_count_mismatch(self):
        issues = check_measurement_row_integrity(
            {
                "document_alias": "RATECON_002",
                "span_normalized_stop_count": 29,
                "span_pickup_count": 13,
                "span_delivery_count": 14,
                "span_unknown_count": 0,
            }
        )

        self.assertIn(ISSUE_SPAN_TYPE_COUNT_MISMATCH, _issue_codes(issues))

    def test_detects_date_denominator_mismatch(self):
        issues = check_measurement_row_integrity(
            {
                "document_alias": "RATECON_003",
                "normalized_stop_count": 2,
                "pickup_count": 1,
                "delivery_count": 1,
                "unknown_stop_count": 0,
                "stop_field_status_counts": {
                    "date": {"resolved": 1, "missing": 0},
                },
            }
        )

        self.assertIn(ISSUE_FIELD_STATUS_DENOMINATOR_MISMATCH, _issue_codes(issues))

    def test_detects_span_field_denominator_mismatch(self):
        issues = check_measurement_row_integrity(
            {
                "document_alias": "RATECON_004",
                "span_normalized_stop_count": 3,
                "span_pickup_count": 1,
                "span_delivery_count": 1,
                "span_unknown_count": 1,
                "span_date_resolved_count": 1,
                "span_date_missing_count": 1,
            }
        )

        self.assertIn(
            ISSUE_SPAN_FIELD_STATUS_DENOMINATOR_MISMATCH,
            _issue_codes(issues),
        )

    def test_passes_valid_fake_row(self):
        issues = check_measurement_row_integrity(
            {
                "document_alias": "RATECON_005",
                "normalized_stop_count": 2,
                "pickup_count": 1,
                "delivery_count": 1,
                "unknown_stop_count": 0,
                "stop_review_required_count": 2,
                "stop_field_status_counts": {
                    "date": {"resolved": 1, "missing": 1},
                    "time": {"resolved": 0, "missing": 2},
                },
                "span_normalized_stop_count": 2,
                "span_pickup_count": 1,
                "span_delivery_count": 1,
                "span_unknown_count": 0,
                "span_review_required_count": 2,
                "span_date_resolved_count": 1,
                "span_date_missing_count": 1,
                "span_time_resolved_count": 0,
                "span_time_missing_count": 2,
            }
        )

        self.assertEqual(issues, [])

    def test_detects_negative_counts_and_ocr_denominator_issue(self):
        issues = check_measurement_row_integrity(
            {
                "document_alias": "RATECON_006",
                "normalized_stop_count": -1,
                "extraction_status": "EMPTY_TEXT",
                "normal_load_movement": True,
            }
        )

        codes = _issue_codes(issues)
        self.assertIn(ISSUE_NEGATIVE_COUNT, codes)
        self.assertIn(ISSUE_OCR_DOC_COUNTED_AS_NORMAL_FAILURE, codes)

    def test_aggregate_integrity_and_summary_are_safe(self):
        issues = check_measurement_aggregate_integrity(
            {
                "span_normalized_stop_count_total": 4,
                "span_pickup_count_total": 2,
                "span_delivery_count_total": 1,
                "span_unknown_count_total": 0,
            }
        )
        summary = summarize_integrity_issues(issues)
        payload = json.loads(json.dumps(summary, sort_keys=True))

        self.assertIn(ISSUE_SPAN_TYPE_COUNT_MISMATCH, summary["issue_counts"])
        self.assertFalse(payload["raw_text_included"])
        self.assertTrue(payload["private_values_redacted"])


if __name__ == "__main__":
    unittest.main()
