import json
import unittest
from pathlib import Path

from app.document_ai.field_candidate_provenance import (
    adapt_ratecon_candidate_to_field_candidate,
)
from app.document_ai.load_identifier_candidate_adapter_provenance import (
    LOAD_ADAPTER_ROUNDTRIP_COMPLETE,
    LOAD_ADAPTER_ROUNDTRIP_LOST_PAGE_LINE,
    LOAD_ADAPTER_ROUNDTRIP_MISSING_INPUT_DETAIL,
    LOAD_ADAPTER_ROUNDTRIP_PRESERVED_PARTIAL_DETAIL,
    redacted_adapter_provenance_row,
    summarize_adapter_provenance_roundtrip,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_candidate_adapter_provenance"


class RateconLoadCandidateAdapterProvenanceTests(unittest.TestCase):
    def _fixture(self, name: str) -> dict:
        return json.loads((FIXTURES / name / "case.json").read_text(encoding="utf-8"))

    def test_legacy_load_candidate_adapter_preserves_existing_metadata(self):
        candidate = {
            "field_name": "load_number",
            "candidate_id": "cand-load-1",
            "raw_value": "LOAD12345",
            "normalized_value": "LOAD12345",
            "confidence": "HIGH",
            "source": "label_pattern",
            "label": "Load #",
            "page_number": "1",
            "line_number": "5",
            "pairing_method": "same_row",
            "context_before": "Header",
            "context_after": "Pickup",
        }

        adapted = adapt_ratecon_candidate_to_field_candidate(candidate)
        metadata = adapted["metadata"]

        self.assertEqual("LOAD12345", adapted["value"])
        self.assertEqual("cand-load-1", metadata["candidate_id"])
        self.assertEqual("1", metadata["page_number"])
        self.assertEqual("5", metadata["line_index"])
        self.assertEqual("5", metadata["line_number"])
        self.assertEqual("label_pattern", metadata["source"])
        self.assertEqual("same_row", metadata["pairing_method"])
        self.assertEqual("present", metadata["label_text_status"])
        self.assertEqual("present", metadata["value_text_status"])
        self.assertEqual("present", metadata["neighbor_context_status"])
        self.assertTrue(metadata["adapter_provenance_preserved"])

    def test_missing_input_detail_stays_missing_and_is_not_invented(self):
        adapted = adapt_ratecon_candidate_to_field_candidate(
            {
                "field_name": "load_number",
                "raw_value": "LOAD12345",
                "normalized_value": "LOAD12345",
                "confidence": "HIGH",
            }
        )
        metadata = adapted["metadata"]
        summary = summarize_adapter_provenance_roundtrip(
            {"field_name": "load_number", "raw_value": "LOAD12345"},
            adapted,
        )

        self.assertNotIn("page_number", metadata)
        self.assertNotIn("line_index", metadata)
        self.assertNotIn("pairing_method", metadata)
        self.assertEqual(
            LOAD_ADAPTER_ROUNDTRIP_MISSING_INPUT_DETAIL,
            summary["adapter_roundtrip_status"],
        )

    def test_fixture_roundtrip_statuses_are_pinned(self):
        for fixture_dir in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
            with self.subTest(fixture=fixture_dir.name):
                payload = self._fixture(fixture_dir.name)
                summary = summarize_adapter_provenance_roundtrip(
                    payload["input_candidate"],
                    payload["output_candidate"],
                )
                self.assertEqual(payload["expected_status"], summary["adapter_roundtrip_status"])

    def test_partial_detail_and_page_line_loss_are_classified(self):
        partial = self._fixture("partial_detail_preserved")
        lost = self._fixture("page_line_lost")

        partial_summary = summarize_adapter_provenance_roundtrip(
            partial["input_candidate"],
            partial["output_candidate"],
        )
        lost_summary = summarize_adapter_provenance_roundtrip(
            lost["input_candidate"],
            lost["output_candidate"],
        )

        self.assertEqual(
            LOAD_ADAPTER_ROUNDTRIP_PRESERVED_PARTIAL_DETAIL,
            partial_summary["adapter_roundtrip_status"],
        )
        self.assertEqual(
            LOAD_ADAPTER_ROUNDTRIP_LOST_PAGE_LINE,
            lost_summary["adapter_roundtrip_status"],
        )

    def test_redacted_diagnostic_row_never_prints_values_by_default(self):
        row = redacted_adapter_provenance_row(
            {
                "field_name": "load_number",
                "candidate_id": "cand-redacted",
                "raw_value": "LOAD12345",
                "source": "native_text",
                "page_number": "1",
                "line_number": "5",
                "pairing_method": "same_row",
            }
        )
        included = redacted_adapter_provenance_row(
            {
                "field_name": "load_number",
                "candidate_id": "cand-redacted",
                "raw_value": "LOAD12345",
                "source": "native_text",
                "page_number": "1",
                "line_number": "5",
                "pairing_method": "same_row",
            },
            include_private_values=True,
        )

        self.assertEqual("[redacted]", row["value_preview"])
        self.assertNotIn("LOAD12345", json.dumps(row))
        self.assertEqual("LOAD12345", included["value_preview"])

    def test_complete_fixture_uses_complete_status_constant(self):
        payload = self._fixture("complete_roundtrip")
        summary = summarize_adapter_provenance_roundtrip(
            payload["input_candidate"],
            payload["output_candidate"],
        )

        self.assertEqual(LOAD_ADAPTER_ROUNDTRIP_COMPLETE, summary["adapter_roundtrip_status"])


if __name__ == "__main__":
    unittest.main()
