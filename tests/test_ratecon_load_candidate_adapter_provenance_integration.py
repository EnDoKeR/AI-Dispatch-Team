import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app.document_ai.field_candidate_provenance import (
    adapt_ratecon_candidate_to_field_candidate,
)
from app.document_ai.field_candidate_resolver import FIELD_LOAD_NUMBER, resolve_candidates
from app.document_ai.load_identifier_source_line_serialization import (
    build_load_source_line_serialization_sidecar,
)
from app.document_ai.load_identifier_source_line_detail import (
    build_load_source_line_detail_inventory,
)
from tests.helpers.ratecon_selected_load_regression import run_selected_load_cases


ROOT = Path(__file__).resolve().parents[1]
SERIALIZATION_SCRIPT = ROOT / "scripts" / "create_ratecon_load_source_line_serialization.py"


class RateconLoadCandidateAdapterProvenanceIntegrationTests(unittest.TestCase):
    def _adapted_resolver_row(self, adapted: dict) -> dict:
        metadata = adapted.get("metadata") or {}
        return {
            "document_id": "FakeLoadConfirmationA",
            "field": adapted.get("field"),
            "candidate_id": metadata.get("candidate_id"),
            "candidate_value": adapted.get("value"),
            "source": adapted.get("source"),
            "parser_name": adapted.get("parser_name"),
            "pairing_method": metadata.get("pairing_method"),
            "page_number": metadata.get("page_number") or adapted.get("page"),
            "line_index": metadata.get("line_index"),
            "selected": True,
        }

    def test_adapter_output_improves_sidecar_roundtrip_status(self):
        generated = {
            "document_id": "FakeLoadConfirmationA",
            "field": "load_number",
            "candidate_id": "cand-load-1",
            "candidate_value": "LOAD12345",
            "source": "label_pattern",
            "parser_name": "load_identifier",
            "pairing_method": "same_row",
            "page_number": "1",
            "line_index": "5",
            "selected": True,
        }
        adapted = adapt_ratecon_candidate_to_field_candidate(
            {
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
            },
            parser_name="load_identifier",
        )
        payload = build_load_source_line_serialization_sidecar(
            generated_rows=[generated],
            resolver_rows=[self._adapted_resolver_row(adapted)],
        )
        row = payload["serialization_rows"][0]

        self.assertEqual("adapter_roundtrip_complete", row["adapter_roundtrip_status"])
        self.assertEqual(1, payload["summary"]["adapter_detail_preserved_count"])
        self.assertEqual(0, payload["summary"]["adapter_detail_lost_count"])
        self.assertEqual("lost_in_shadow_audit", row["serialization_loss_bucket"])

    def test_resolver_trace_receives_preserved_source_line_metadata(self):
        adapted = adapt_ratecon_candidate_to_field_candidate(
            {
                "field_name": "load_number",
                "candidate_id": "cand-trace",
                "raw_value": "LOAD12345",
                "normalized_value": "LOAD12345",
                "confidence": "HIGH",
                "source": "label_pattern",
                "label": "Load #",
                "page_number": "1",
                "line_number": "5",
                "pairing_method": "same_row",
            },
            parser_name="load_identifier",
        )
        result = resolve_candidates([adapted], field_names=[FIELD_LOAD_NUMBER])
        trace = result["resolver_decision_traces"][FIELD_LOAD_NUMBER]["selected_candidate"]
        metadata = trace["metadata_summary"]

        self.assertEqual("LOAD12345", result["resolved_fields"][FIELD_LOAD_NUMBER]["value"])
        self.assertEqual("cand-trace", trace["candidate_id"])
        self.assertEqual("cand-trace", metadata["candidate_id"])
        self.assertEqual("1", metadata["page_number"])
        self.assertEqual("5", metadata["line_index"])
        self.assertEqual("same_row", metadata["pairing_method"])
        self.assertTrue(metadata["adapter_provenance_preserved"])

    def test_selected_load_regression_outputs_stay_unchanged(self):
        by_id = {result["case_id"]: result for result in run_selected_load_cases()}

        self.assertEqual("FAKE-LOAD-001", by_id["explicit_load_number_header"]["selected_value"])
        self.assertEqual("missing", by_id["po_number_not_load_when_current_behavior_rejects"]["status"])
        self.assertEqual("needs_review", by_id["broker_reference_only"]["status"])
        self.assertEqual("resolved", by_id["table_neighbor_wrong_cell_known_debt"]["status"])

    def test_detail_inventory_consumes_adapter_roundtrip_status(self):
        payload = build_load_source_line_detail_inventory(
            serialization_rows=[
                {
                    "document_id": "FakeLoadConfirmationA",
                    "field": "load_number",
                    "candidate_id": "cand-load-1",
                    "source": "native_text",
                    "pairing_method": "same_row",
                    "page_number": "1",
                    "line_index": "5",
                    "selected": "true",
                    "serialization_loss_bucket": "complete_detail_serialized",
                    "detail_loss_bucket": "candidate_has_complete_source_detail",
                    "detail_loss_stage": "none",
                    "detail_loss_reason": "Complete detail roundtrip.",
                    "adapter_roundtrip_status": "adapter_roundtrip_complete",
                    "adapter_loss_reason": "Adapter preserved complete detail.",
                }
            ],
        )
        row = payload["detail_rows"][0]

        self.assertEqual("adapter_roundtrip_complete", row["adapter_roundtrip_status"])
        self.assertEqual(1, payload["summary"]["adapter_detail_preserved_count"])
        self.assertEqual(0, payload["summary"]["adapter_detail_lost_count"])

    def test_direct_complete_adapter_roundtrip_fixture_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            generated = tmp_path / "generated.csv"
            resolver = tmp_path / "resolver.csv"
            audit = tmp_path / "audit.jsonl"
            eval_dir = tmp_path / "eval"
            eval_dir.mkdir()
            generated.write_text(
                "document_id,field,candidate_id,candidate_value,source,parser_name,pairing_method,page_number,line_index,selected\n"
                "FakeLoadConfirmationA,load_number,cand-load-1,LOAD12345,label_pattern,load_identifier,same_row,1,5,true\n",
                encoding="utf-8",
            )
            resolver.write_text(
                "document_id,field,candidate_id,candidate_value,source,parser_name,pairing_method,page_number,line_index,selected\n"
                "FakeLoadConfirmationA,load_number,cand-load-1,LOAD12345,native_text,load_identifier,same_row,1,5,true\n",
                encoding="utf-8",
            )
            audit.write_text("", encoding="utf-8")
            (eval_dir / "private_selected_load_selected_rows.csv").write_text(
                "document_id,field,selected_candidate_id,selected_value,selected_source,pairing_method,selected_page_index,selected_line_index\n"
                "FakeLoadConfirmationA,load_number,cand-load-1,LOAD12345,native_text,same_row,1,5\n",
                encoding="utf-8",
            )
            output_dir = tmp_path / ".local_outputs" / "adapter_roundtrip"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SERIALIZATION_SCRIPT),
                    "--generated-candidates",
                    str(generated),
                    "--resolver-trace",
                    str(resolver),
                    "--audit",
                    str(audit),
                    "--eval-dir",
                    str(eval_dir),
                    "--output-dir",
                    str(output_dir),
                    "--confirm-private-local-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            with (output_dir / "load_source_line_serialization_rows.csv").open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = [dict(row) for row in csv.DictReader(handle)]
            payload = json.loads(
                (output_dir / "load_source_line_serialization_summary.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual("adapter_roundtrip_complete", rows[0]["adapter_roundtrip_status"])
        self.assertEqual(1, payload["summary"]["adapter_detail_preserved_count"])
        self.assertEqual(0, payload["summary"]["adapter_detail_lost_count"])
        self.assertNotIn("LOAD12345", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
