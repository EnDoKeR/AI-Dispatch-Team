import json
import unittest

from app.document_ai.stop_review_pattern_classifier import (
    PATTERN_DATE_CANDIDATE_NOT_ATTACHED,
    PATTERN_DUPLICATE_STOP_GROUPS,
    PATTERN_TABLE_CELL_OVER_GROUPING,
    PATTERN_TERMS_BILLING_NOISE,
    classify_stop_review_packet_patterns,
)


def _row(
    alias="RATECON_001",
    stop_id="STOP_001",
    stop_type="pickup",
    sequence="1",
    field_name="location",
    status="resolved",
    evidence_type="section_context",
    warning_codes="",
    value="",
):
    return {
        "document_alias": alias,
        "stop_id": stop_id,
        "stop_type": stop_type,
        "sequence": sequence,
        "field_name": field_name,
        "status": status,
        "confidence_bucket": "HIGH",
        "evidence_type": evidence_type,
        "page_number": "1",
        "warning_codes": warning_codes,
        "selected_value_local_only": value,
    }


class StopReviewPatternClassifierTests(unittest.TestCase):
    def test_fake_duplicate_groups_classified_without_values_serialized(self):
        rows = [
            _row(stop_id="STOP_001", value="FAKE_PRIVATE_LOCATION"),
            _row(stop_id="STOP_002", sequence="2", value="FAKE_PRIVATE_LOCATION"),
        ]

        result = classify_stop_review_packet_patterns(
            rows,
            include_private_values_local_only=True,
        )
        payload = json.dumps(result)

        self.assertEqual(result["pattern_counts"][PATTERN_DUPLICATE_STOP_GROUPS], 1)
        self.assertNotIn("FAKE_PRIVATE_LOCATION", payload)
        self.assertFalse(result["private_values_included"])

    def test_fake_table_cell_overgrouping_classified(self):
        rows = []
        for index in range(1, 7):
            rows.append(
                _row(
                    stop_id=f"STOP_{index:03d}",
                    sequence=str(index),
                    evidence_type="table_cell",
                )
            )
            rows.append(
                _row(
                    stop_id=f"STOP_{index:03d}",
                    sequence=str(index),
                    field_name="date",
                    status="missing",
                    evidence_type="table_cell",
                )
            )

        result = classify_stop_review_packet_patterns(rows)

        self.assertIn(PATTERN_TABLE_CELL_OVER_GROUPING, result["pattern_counts"])

    def test_fake_date_not_attached_classified(self):
        rows = [
            _row(stop_id="STOP_001"),
            _row(stop_id="STOP_001", field_name="date", status="missing"),
            _row(stop_id="STOP_002", sequence="2", stop_type="delivery"),
            _row(stop_id="STOP_002", sequence="2", stop_type="delivery", field_name="date", status="missing"),
        ]

        result = classify_stop_review_packet_patterns(rows)

        self.assertIn(PATTERN_DATE_CANDIDATE_NOT_ATTACHED, result["pattern_counts"])

    def test_fake_terms_noise_classified(self):
        rows = [
            _row(warning_codes="stop_group_noise_terms_or_billing"),
            _row(field_name="date", status="missing", warning_codes="stop_group_noise_terms_or_billing"),
        ]

        result = classify_stop_review_packet_patterns(rows)

        self.assertIn(PATTERN_TERMS_BILLING_NOISE, result["pattern_counts"])

    def test_safe_serialization_excludes_values(self):
        rows = [_row(value="FAKE_SECRET_STOP_VALUE")]

        result = classify_stop_review_packet_patterns(
            rows,
            include_private_values_local_only=True,
        )

        self.assertNotIn("FAKE_SECRET_STOP_VALUE", json.dumps(result))


if __name__ == "__main__":
    unittest.main()

