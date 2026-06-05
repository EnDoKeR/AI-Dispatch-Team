import json
import unittest
from pathlib import Path

from app.document_ai.load_identifier_resolver_to_audit_provenance import (
    STATUS_CANDIDATE_ID_LOST,
    STATUS_CANDIDATE_NOT_COMPARABLE,
    STATUS_MISSING_AUDIT_ROW,
    STATUS_PAGE_LINE_LOST,
    STATUS_PAIRING_METHOD_LOST,
    STATUS_PRESERVED,
    STATUS_SELECTED_FLAG_LOST,
    STATUS_SOURCE_LOST,
    build_resolver_to_audit_provenance_sidecar,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_resolver_to_audit_provenance"


class RateconLoadResolverToAuditProvenanceTests(unittest.TestCase):
    def test_preserved_resolver_row_reports_preserved_and_redacts_value(self):
        payload = build_resolver_to_audit_provenance_sidecar(
            resolver_rows=[
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "load_number",
                    "candidate_id": "cand-load-1",
                    "source": "native_text",
                    "pairing_method": "same_row",
                    "page_number": 1,
                    "line_index": 10,
                    "bbox_available": True,
                    "resolver_selected": True,
                    "candidate_value": "LOAD12345",
                }
            ],
            audit_rows=[
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "load_number",
                    "candidate_id": "cand-load-1",
                    "source": "native_text",
                    "pairing_method": "same_row",
                    "page_number": 1,
                    "line_index": 10,
                    "bbox_available": True,
                    "selected": True,
                    "candidate_value": "LOAD12345",
                }
            ],
        )

        self.assertEqual(STATUS_PRESERVED, payload["rows"][0]["resolver_to_audit_status"])
        self.assertEqual("[redacted]", payload["rows"][0]["value_preview"])
        self.assertTrue(payload["summary"]["private_values_redacted"])
        self.assertFalse(payload["summary"]["pdf_processing_attempted"])
        self.assertFalse(payload["summary"]["ocr_attempted"])
        self.assertFalse(payload["summary"]["google_called"])
        self.assertFalse(payload["summary"]["model_or_cloud_called"])

    def test_private_values_require_explicit_local_flag(self):
        resolver = {
            "document_id": "FakeLoadConfirmationA",
            "field": "load_number",
            "candidate_id": "cand-load-1",
            "source": "native_text",
            "pairing_method": "same_row",
            "page_number": 1,
            "line_index": 10,
            "candidate_value": "LOAD12345",
        }
        redacted = build_resolver_to_audit_provenance_sidecar(
            resolver_rows=[resolver],
            audit_rows=[resolver],
        )
        included = build_resolver_to_audit_provenance_sidecar(
            resolver_rows=[resolver],
            audit_rows=[resolver],
            include_private_values=True,
        )

        self.assertNotIn("LOAD12345", json.dumps(redacted["summary"]))
        self.assertEqual("[redacted]", redacted["rows"][0]["value_preview"])
        self.assertEqual("LOAD12345", included["rows"][0]["value_preview"])

    def test_loss_statuses_are_classified_without_inference(self):
        base_resolver = {
            "document_id": "FakeLoadConfirmationA",
            "field": "load_number",
            "candidate_id": "cand-load-1",
            "source": "native_text",
            "pairing_method": "same_row",
            "page_number": 1,
            "line_index": 10,
            "resolver_selected": True,
        }
        cases = [
            ([], STATUS_MISSING_AUDIT_ROW),
            ([{**base_resolver, "candidate_id": "", "selected": True}], STATUS_CANDIDATE_ID_LOST),
            ([{**base_resolver, "source": ""}], STATUS_SOURCE_LOST),
            ([{**base_resolver, "page_number": "", "line_index": ""}], STATUS_PAGE_LINE_LOST),
            ([{**base_resolver, "pairing_method": ""}], STATUS_PAIRING_METHOD_LOST),
            ([{**base_resolver, "selected": False}], STATUS_SELECTED_FLAG_LOST),
        ]
        for audit_rows, expected in cases:
            with self.subTest(expected=expected):
                payload = build_resolver_to_audit_provenance_sidecar(
                    resolver_rows=[base_resolver],
                    audit_rows=audit_rows,
                )
                self.assertEqual(expected, payload["rows"][0]["resolver_to_audit_status"])

    def test_missing_candidate_id_is_not_comparable(self):
        payload = build_resolver_to_audit_provenance_sidecar(
            resolver_rows=[
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "load_number",
                    "source": "native_text",
                    "pairing_method": "same_row",
                    "page_number": 1,
                }
            ],
            audit_rows=[],
        )

        self.assertEqual(
            STATUS_CANDIDATE_NOT_COMPARABLE,
            payload["rows"][0]["resolver_to_audit_status"],
        )


if __name__ == "__main__":
    unittest.main()
