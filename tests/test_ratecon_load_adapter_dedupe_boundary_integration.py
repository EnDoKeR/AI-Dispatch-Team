import csv
import unittest
from pathlib import Path

from app.document_ai.load_identifier_generated_provenance_boundary import (
    BOUNDARY_ADAPTER_TO_DEDUPE_LOSS,
    BOUNDARY_DEDUPE_TO_RESOLVER_LOSS,
    BOUNDARY_GENERATION_TO_ADAPTER_LOSS,
    compare_generated_provenance_boundaries,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_adapter_dedupe_stage_sidecars"


def _rows(fixture: str) -> list[dict[str, str]]:
    with (FIXTURES / fixture / "stage_rows.csv").open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


class RateconLoadAdapterDedupeBoundaryIntegrationTests(unittest.TestCase):
    def test_stage_unavailable_keeps_generation_to_adapter_boundary_unresolved(self):
        payload = compare_generated_provenance_boundaries(
            _rows("current_like_generation_to_adapter_loss")
        )

        self.assertEqual(
            BOUNDARY_GENERATION_TO_ADAPTER_LOSS,
            payload["summary"]["first_loss_boundary"],
        )

    def test_adapter_rows_visible_move_boundary_to_dedupe(self):
        payload = compare_generated_provenance_boundaries(_rows("adapter_to_dedupe_loss"))

        self.assertEqual(
            BOUNDARY_ADAPTER_TO_DEDUPE_LOSS,
            payload["summary"]["first_loss_boundary"],
        )

    def test_dedupe_rows_visible_move_boundary_to_resolver(self):
        payload = compare_generated_provenance_boundaries(_rows("dedupe_input_output_complete"))

        self.assertEqual(
            BOUNDARY_DEDUPE_TO_RESOLVER_LOSS,
            payload["summary"]["first_loss_boundary"],
        )
        self.assertFalse(payload["summary"]["pdf_processing_attempted"])
        self.assertFalse(payload["summary"]["ocr_attempted"])
        self.assertFalse(payload["summary"]["google_called"])
        self.assertFalse(payload["summary"]["model_or_cloud_called"])


if __name__ == "__main__":
    unittest.main()
