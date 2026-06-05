import json
import unittest

from app.document_ai.load_identifier_generated_resolver_provenance import (
    ROUNDTRIP_COMPLETE,
    ROUNDTRIP_UNMEASURABLE,
    STAGE_GENERATED_DETAIL_AVAILABLE,
    STAGE_GENERATED_DETAIL_MISSING,
    STAGE_LOST_BETWEEN_GENERATION_AND_ADAPTER,
    build_load_generated_resolver_provenance_sidecars,
)


class RateconLoadGeneratedResolverProvenanceTests(unittest.TestCase):
    def _complete_candidate(self):
        return {
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

    def test_full_roundtrip_preserves_existing_stage_metadata(self):
        candidate = self._complete_candidate()
        payload = build_load_generated_resolver_provenance_sidecars(
            generated_rows=[candidate],
            adapter_input_rows=[candidate],
            adapter_output_rows=[candidate],
            dedupe_input_rows=[candidate],
            dedupe_output_rows=[candidate],
            resolver_rows=[candidate],
            audit_rows=[candidate],
            serialization_rows=[candidate],
        )

        row = payload["loss_rows"][0]
        self.assertEqual(STAGE_GENERATED_DETAIL_AVAILABLE, row["stage_loss_bucket"])
        self.assertEqual(ROUNDTRIP_COMPLETE, row["generated_resolver_roundtrip_status"])
        self.assertEqual(1, payload["summary"]["complete_roundtrip_count"])
        self.assertEqual(1, payload["summary"]["generated_candidate_detail_available_count"])
        self.assertEqual(1, payload["summary"]["resolver_visible_detail_available_count"])
        self.assertEqual("[redacted]", payload["generated_rows"][0]["value_preview"])
        self.assertFalse(payload["summary"]["pdf_processing_attempted"])
        self.assertFalse(payload["summary"]["ocr_attempted"])
        self.assertFalse(payload["summary"]["google_called"])
        self.assertFalse(payload["summary"]["model_or_cloud_called"])

    def test_missing_generated_detail_is_pinned_and_not_invented(self):
        payload = build_load_generated_resolver_provenance_sidecars(
            generated_rows=[
                {
                    "document_id": "FakeLoadConfirmationB",
                    "field": "load_number",
                    "candidate_id": "cand-load-2",
                    "candidate_value": "LOAD22345",
                    "source": "table_key_value_row",
                    "pairing_method": "same_row",
                }
            ]
        )

        row = payload["loss_rows"][0]
        self.assertEqual(STAGE_GENERATED_DETAIL_MISSING, row["stage_loss_bucket"])
        self.assertEqual(0, payload["summary"]["complete_roundtrip_count"])
        self.assertEqual(0, payload["summary"]["resolver_visible_candidate_count"])

    def test_generation_to_adapter_loss_is_pinned(self):
        payload = build_load_generated_resolver_provenance_sidecars(
            generated_rows=[self._complete_candidate()]
        )

        row = payload["loss_rows"][0]
        self.assertEqual(
            STAGE_LOST_BETWEEN_GENERATION_AND_ADAPTER,
            row["stage_loss_bucket"],
        )
        self.assertEqual("candidate_adapter", row["generated_resolver_loss_stage"])

    def test_eval_audit_only_artifacts_are_unmeasurable_not_complete(self):
        payload = build_load_generated_resolver_provenance_sidecars(
            audit_rows=[
                {
                    "document_id": "FakeLoadConfirmationI",
                    "field": "load_number",
                    "candidate_id": "cand-load-9",
                    "candidate_value": "REF33333",
                    "source": "reference_number",
                }
            ]
        )

        row = payload["loss_rows"][0]
        self.assertEqual("unknown", row["stage_loss_bucket"])
        self.assertEqual(ROUNDTRIP_UNMEASURABLE, row["generated_resolver_roundtrip_status"])
        self.assertEqual(
            ROUNDTRIP_UNMEASURABLE,
            payload["summary"]["current_artifacts_status"],
        )

    def test_private_values_are_explicit_only(self):
        candidate = self._complete_candidate()
        redacted = build_load_generated_resolver_provenance_sidecars(
            generated_rows=[candidate]
        )
        included = build_load_generated_resolver_provenance_sidecars(
            generated_rows=[candidate],
            include_private_values=True,
        )

        self.assertNotIn("LOAD12345", json.dumps(redacted))
        self.assertEqual("[redacted]", redacted["generated_rows"][0]["value_preview"])
        self.assertEqual("LOAD12345", included["generated_rows"][0]["value_preview"])


if __name__ == "__main__":
    unittest.main()
