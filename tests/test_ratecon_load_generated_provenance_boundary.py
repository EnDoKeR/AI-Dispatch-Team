import csv
import unittest
from pathlib import Path

from app.document_ai.load_identifier_generated_provenance_boundary import (
    BOUNDARY_ADAPTER_TO_DEDUPE_LOSS,
    BOUNDARY_AUDIT_TO_EVALUATOR_LOSS,
    BOUNDARY_CANDIDATE_NOT_COMPARABLE,
    BOUNDARY_DEDUPE_TO_RESOLVER_LOSS,
    BOUNDARY_EVALUATOR_TO_SIDECAR_LOSS,
    BOUNDARY_GENERATION_TO_ADAPTER_LOSS,
    BOUNDARY_INPUT_DETAIL_MISSING,
    BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP,
    BOUNDARY_RESOLVER_TO_AUDIT_LOSS,
    BOUNDARY_STAGE_UNAVAILABLE,
    compare_generated_provenance_boundaries,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_generated_provenance_later_boundary"


class RateconLoadGeneratedProvenanceBoundaryTests(unittest.TestCase):
    def _fixture_rows(self, fixture: str) -> list[dict[str, str]]:
        with (FIXTURES / fixture / "load_generated_provenance_boundary_stage_rows.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    def test_boundary_statuses_are_pinned(self):
        cases = {
            "generation_to_adapter_loss": BOUNDARY_GENERATION_TO_ADAPTER_LOSS,
            "adapter_to_dedupe_loss": BOUNDARY_ADAPTER_TO_DEDUPE_LOSS,
            "dedupe_to_resolver_loss": BOUNDARY_DEDUPE_TO_RESOLVER_LOSS,
            "resolver_to_audit_loss": BOUNDARY_RESOLVER_TO_AUDIT_LOSS,
            "audit_to_evaluator_loss": BOUNDARY_AUDIT_TO_EVALUATOR_LOSS,
            "evaluator_to_sidecar_loss": BOUNDARY_EVALUATOR_TO_SIDECAR_LOSS,
            "complete_roundtrip": BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP,
            "input_detail_missing": BOUNDARY_INPUT_DETAIL_MISSING,
            "stage_unavailable": BOUNDARY_STAGE_UNAVAILABLE,
            "current_run_later_loss_like": BOUNDARY_GENERATION_TO_ADAPTER_LOSS,
        }
        for fixture, expected in cases.items():
            with self.subTest(fixture=fixture):
                payload = compare_generated_provenance_boundaries(self._fixture_rows(fixture))

                self.assertEqual(expected, payload["summary"]["first_loss_boundary"])
                self.assertEqual(expected, payload["boundary_rows"][0]["loss_boundary"])
                self.assertFalse(payload["summary"]["private_values_included"])
                self.assertTrue(payload["summary"]["private_values_redacted"])
                self.assertFalse(payload["summary"]["pdf_processing_attempted"])
                self.assertFalse(payload["summary"]["ocr_attempted"])
                self.assertFalse(payload["summary"]["google_called"])
                self.assertFalse(payload["summary"]["model_or_cloud_called"])

    def test_missing_candidate_id_is_not_fabricated(self):
        payload = compare_generated_provenance_boundaries(
            [
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "load_number",
                    "stage": "generated",
                    "source": "native_layout",
                    "pairing_method": "nearby_row",
                    "page_number": "1",
                }
            ]
        )

        self.assertEqual(BOUNDARY_CANDIDATE_NOT_COMPARABLE, payload["summary"]["first_loss_boundary"])
        self.assertEqual("", payload["boundary_rows"][0]["candidate_id"])

    def test_non_load_rows_are_ignored(self):
        payload = compare_generated_provenance_boundaries(
            [
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "total_carrier_rate",
                    "stage": "generated",
                    "candidate_id": "rate-1",
                }
            ]
        )

        self.assertEqual(1, payload["summary"]["candidate_count"])
        self.assertEqual(BOUNDARY_CANDIDATE_NOT_COMPARABLE, payload["summary"]["first_loss_boundary"])


if __name__ == "__main__":
    unittest.main()
