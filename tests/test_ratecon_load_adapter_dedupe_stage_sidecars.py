import csv
import json
import unittest
from pathlib import Path

from app.document_ai.load_identifier_generated_resolver_provenance import (
    ADAPTER_OUTPUT_DETAIL_LOST,
    ADAPTER_STAGE_COMPLETE,
    DEDUPE_OUTPUT_DETAIL_LOST,
    DEDUPE_STAGE_COMPLETE,
    build_load_generated_resolver_provenance_sidecars,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_adapter_dedupe_stage_sidecars"


def _rows(fixture: str) -> list[dict[str, str]]:
    with (FIXTURES / fixture / "stage_rows.csv").open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _stage(rows: list[dict[str, str]], stage: str) -> list[dict[str, str]]:
    return [row for row in rows if row.get("stage") == stage]


class RateconLoadAdapterDedupeStageSidecarsTests(unittest.TestCase):
    def test_adapter_and_dedupe_complete_preserve_metadata(self):
        rows = _rows("dedupe_input_output_complete")
        payload = build_load_generated_resolver_provenance_sidecars(
            generated_rows=_stage(rows, "generated"),
            adapter_input_rows=_stage(rows, "adapter_input"),
            adapter_output_rows=_stage(rows, "adapter_output"),
            dedupe_input_rows=_stage(rows, "dedupe_input"),
            dedupe_output_rows=_stage(rows, "dedupe_output"),
        )

        summary = payload["summary"]
        self.assertEqual(1, summary["adapter_input_count"])
        self.assertEqual(1, summary["adapter_output_count"])
        self.assertEqual(1, summary["dedupe_input_count"])
        self.assertEqual(1, summary["dedupe_output_count"])
        self.assertEqual({ADAPTER_STAGE_COMPLETE: 1}, summary["adapter_stage_status_counts"])
        self.assertEqual({DEDUPE_STAGE_COMPLETE: 1}, summary["dedupe_stage_status_counts"])
        self.assertNotIn("LOAD12345", json.dumps(payload))
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["google_called"])
        self.assertFalse(summary["model_or_cloud_called"])

    def test_adapter_output_lost_detail_is_classified_without_inference(self):
        rows = _rows("adapter_output_lost_detail")
        payload = build_load_generated_resolver_provenance_sidecars(
            generated_rows=_stage(rows, "generated"),
            adapter_input_rows=_stage(rows, "adapter_input"),
            adapter_output_rows=_stage(rows, "adapter_output"),
        )

        summary = payload["summary"]
        self.assertEqual(1, summary["adapter_detail_lost_count"])
        self.assertEqual(
            {ADAPTER_OUTPUT_DETAIL_LOST: 1},
            summary["adapter_stage_status_counts"],
        )

    def test_dedupe_dropped_and_merged_lineage_are_reported(self):
        merged_rows = _rows("dedupe_merged_detail_preserved")
        dropped_rows = _rows("dedupe_dropped_detail_preserved")
        payload = build_load_generated_resolver_provenance_sidecars(
            dedupe_input_rows=dropped_rows,
            dedupe_output_rows=merged_rows,
        )

        loss_rows = payload["adapter_dedupe_loss_rows"]
        self.assertTrue(any(row["dedupe_dropped"] for row in loss_rows))
        self.assertTrue(any(row["dedupe_merged"] for row in loss_rows))
        self.assertFalse(payload["summary"]["private_values_included"])

    def test_dedupe_output_lost_detail_is_classified(self):
        rows = _rows("adapter_to_dedupe_loss")
        payload = build_load_generated_resolver_provenance_sidecars(
            generated_rows=_stage(rows, "generated"),
            adapter_input_rows=_stage(rows, "adapter_input"),
            adapter_output_rows=_stage(rows, "adapter_output"),
            dedupe_input_rows=_stage(rows, "adapter_output"),
            dedupe_output_rows=[
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "load_number",
                    "stage": "dedupe_output",
                    "candidate_id": "cand-load-1",
                }
            ],
        )

        self.assertEqual(1, payload["summary"]["dedupe_detail_lost_count"])
        self.assertEqual(
            {DEDUPE_OUTPUT_DETAIL_LOST: 1},
            payload["summary"]["dedupe_stage_status_counts"],
        )


if __name__ == "__main__":
    unittest.main()
