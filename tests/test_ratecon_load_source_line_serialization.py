import json
import unittest

from app.document_ai.load_identifier_source_line_serialization import (
    SERIALIZATION_COMPLETE,
    SERIALIZATION_LOST_IN_RESOLVER_TRACE,
    SERIALIZATION_MISSING_PAGE_LINE_AT_GENERATION,
    build_load_source_line_serialization_sidecar,
)


class RateconLoadSourceLineSerializationTests(unittest.TestCase):
    def test_complete_roundtrip_preserves_safe_metadata(self):
        payload = build_load_source_line_serialization_sidecar(
            generated_rows=[
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "load_number",
                    "candidate_id": "cand-load-1",
                    "candidate_value": "LOAD12345",
                    "source": "table_key_value_row",
                    "parser_name": "load_identifier",
                    "pairing_method": "same_row",
                    "page_number": "1",
                    "line_index": "5",
                    "selected": True,
                }
            ],
            resolver_rows=[
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "load_number",
                    "candidate_id": "cand-load-1",
                    "candidate_value": "LOAD12345",
                    "source": "table_key_value_row",
                    "parser_name": "load_identifier",
                    "pairing_method": "same_row",
                    "page_number": "1",
                    "line_index": "5",
                    "selected": True,
                }
            ],
            audit_rows=[
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "load_number",
                    "candidate_id": "cand-load-1",
                    "candidate_value": "LOAD12345",
                    "source": "table_key_value_row",
                    "parser_name": "load_identifier",
                    "pairing_method": "same_row",
                    "page_number": "1",
                    "line_index": "5",
                    "selected": True,
                }
            ],
            evaluator_rows=[
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "load_number",
                    "selected_candidate_id": "cand-load-1",
                    "selected_value": "LOAD12345",
                    "selected_source": "table_key_value_row",
                    "pairing_method": "same_row",
                    "selected_page_index": "1",
                    "selected_line_index": "5",
                }
            ],
        )

        row = payload["serialization_rows"][0]
        self.assertEqual(SERIALIZATION_COMPLETE, row["serialization_loss_bucket"])
        self.assertEqual("cand-load-1", row["candidate_id"])
        self.assertEqual("table", row["source_family"])
        self.assertEqual("same_row", row["pairing_method"])
        self.assertEqual("[redacted]", row["value_preview"])
        self.assertEqual(1, payload["summary"]["complete_detail_serialized_count"])
        self.assertFalse(payload["summary"]["pdf_processing_attempted"])
        self.assertFalse(payload["summary"]["ocr_attempted"])
        self.assertFalse(payload["summary"]["google_called"])
        self.assertFalse(payload["summary"]["model_or_cloud_called"])

    def test_missing_generation_page_line_is_pinned(self):
        payload = build_load_source_line_serialization_sidecar(
            generated_rows=[
                {
                    "document_id": "FakeLoadConfirmationB",
                    "field": "load_number",
                    "candidate_id": "cand-load-2",
                    "candidate_value": "LOAD22345",
                    "source": "native_text",
                    "pairing_method": "native_text",
                }
            ]
        )

        row = payload["serialization_rows"][0]
        self.assertEqual(
            SERIALIZATION_MISSING_PAGE_LINE_AT_GENERATION,
            row["serialization_loss_bucket"],
        )
        self.assertEqual(1, payload["summary"]["missing_at_generation_count"])

    def test_resolver_trace_loss_is_pinned_and_values_are_optional(self):
        base_kwargs = {
            "generated_rows": [
                {
                    "document_id": "FakeLoadConfirmationC",
                    "field": "load_number",
                    "candidate_id": "cand-load-3",
                    "candidate_value": "LOAD32345",
                    "source": "nearby_row",
                    "pairing_method": "nearby_row",
                    "page_number": "2",
                    "line_index": "9",
                }
            ],
            "resolver_rows": [
                {
                    "document_id": "FakeLoadConfirmationC",
                    "field": "load_number",
                    "candidate_id": "cand-load-3",
                    "candidate_value": "LOAD32345",
                    "source": "nearby_row",
                    "pairing_method": "nearby_row",
                }
            ],
        }

        redacted = build_load_source_line_serialization_sidecar(**base_kwargs)
        included = build_load_source_line_serialization_sidecar(
            **base_kwargs,
            include_private_values=True,
        )

        self.assertEqual(
            SERIALIZATION_LOST_IN_RESOLVER_TRACE,
            redacted["serialization_rows"][0]["serialization_loss_bucket"],
        )
        self.assertEqual("[redacted]", redacted["serialization_rows"][0]["value_preview"])
        self.assertEqual("LOAD32345", included["serialization_rows"][0]["value_preview"])
        self.assertNotIn("LOAD32345", json.dumps(redacted))
        self.assertTrue(redacted["summary"]["values_redacted"])
        self.assertTrue(included["summary"]["private_values_included"])


if __name__ == "__main__":
    unittest.main()
