import unittest

from app.document_ai.load_identifier_source_line_detail import (
    DETAIL_LOSS_COMPLETE,
    DETAIL_LOSS_MISSING_PAGE_LINE,
    DETAIL_LOSS_DROPPED_BEFORE_AUDIT,
    build_load_source_line_detail_inventory,
)


class RateconLoadSourceLineDetailTests(unittest.TestCase):
    def test_complete_candidate_detail_is_preserved_safely(self):
        payload = build_load_source_line_detail_inventory(
            selected_rows={
                "FakeLoadConfirmationA": {
                    "document_id": "FakeLoadConfirmationA",
                    "selected_value": "LOAD12345",
                    "gold_value": "LOAD12345",
                    "selected_source": "table_key_value_row",
                    "selected_line_index": "5",
                    "selected_page_index": "1",
                }
            },
            audit_rows={
                "FakeLoadConfirmationA": {
                    "document_id": "FakeLoadConfirmationA",
                    "candidate_details": [
                        {
                            "candidate_id": "cand-load-1",
                            "candidate_value": "LOAD12345",
                            "selected": True,
                            "source": "table_key_value_row",
                            "pairing_method": "table_key_value",
                            "page_number": "1",
                            "line_index": "5",
                            "label_text": "Load #",
                            "source_line": "Load # LOAD12345",
                            "neighbor_context": "same row",
                        }
                    ],
                }
            },
            diagnostic_rows={
                "FakeLoadConfirmationA": {
                    "document_id": "FakeLoadConfirmationA",
                    "diagnostic_bucket": "duplicate_same_value_candidates",
                }
            },
        )

        row = payload["detail_rows"][0]
        self.assertEqual(DETAIL_LOSS_COMPLETE, row["detail_loss_bucket"])
        self.assertEqual("table", row["source_family"])
        self.assertEqual("table_key_value", row["pairing_method"])
        self.assertEqual("[redacted]", row["value_preview"])
        self.assertEqual(1, payload["summary"]["complete_source_detail_count"])

    def test_private_values_only_appear_with_explicit_flag(self):
        base_kwargs = {
            "selected_rows": {
                "FakeLoadConfirmationA": {
                    "document_id": "FakeLoadConfirmationA",
                    "selected_value": "LOAD12345",
                    "gold_value": "LOAD12345",
                }
            },
            "audit_rows": {
                "FakeLoadConfirmationA": {
                    "document_id": "FakeLoadConfirmationA",
                    "candidate_details": [
                        {
                            "candidate_id": "cand-load-1",
                            "candidate_value": "LOAD12345",
                            "selected": True,
                            "source": "native_text",
                            "pairing_method": "native_text",
                            "page_number": "1",
                            "line_index": "5",
                            "label_text": "Load #",
                        }
                    ],
                }
            },
        }

        redacted = build_load_source_line_detail_inventory(**base_kwargs)
        included = build_load_source_line_detail_inventory(
            **base_kwargs,
            include_private_values=True,
        )

        self.assertEqual("[redacted]", redacted["detail_rows"][0]["value_preview"])
        self.assertEqual("LOAD12345", included["detail_rows"][0]["value_preview"])
        self.assertFalse(redacted["summary"]["private_values_included"])
        self.assertTrue(included["summary"]["private_values_included"])

    def test_missing_page_line_is_classified(self):
        payload = build_load_source_line_detail_inventory(
            audit_rows={
                "FakeLoadConfirmationB": {
                    "document_id": "FakeLoadConfirmationB",
                    "candidate_details": [
                        {
                            "candidate_id": "cand-load-2",
                            "candidate_value": "LOAD12345",
                            "selected": True,
                            "source": "native_text",
                            "pairing_method": "native_text",
                            "label_text": "Load #",
                        }
                    ],
                }
            }
        )

        self.assertEqual(
            DETAIL_LOSS_MISSING_PAGE_LINE,
            payload["detail_rows"][0]["detail_loss_bucket"],
        )
        self.assertEqual(1, payload["summary"]["missing_page_line_count"])

    def test_dropped_before_audit_is_classified(self):
        payload = build_load_source_line_detail_inventory(
            selected_rows={
                "FakeLoadConfirmationC": {
                    "document_id": "FakeLoadConfirmationC",
                    "selected_value": "LOAD12345",
                    "selected_line_index": "7",
                    "selected_page_index": "1",
                }
            },
            audit_rows={
                "FakeLoadConfirmationC": {
                    "document_id": "FakeLoadConfirmationC",
                    "candidate_details": [
                        {
                            "candidate_id": "cand-load-3",
                            "candidate_value": "LOAD12345",
                            "selected": True,
                            "source": "native_text",
                            "pairing_method": "native_text",
                            "label_text": "Load #",
                        }
                    ],
                }
            },
        )

        self.assertEqual(
            DETAIL_LOSS_DROPPED_BEFORE_AUDIT,
            payload["detail_rows"][0]["detail_loss_bucket"],
        )
        self.assertEqual(1, payload["summary"]["dropped_detail_count"])


if __name__ == "__main__":
    unittest.main()
