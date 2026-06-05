import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.run_private_ratecon_measurement import main


class RunPrivateRateconMeasurementLoadProvenanceSidecarsTests(unittest.TestCase):
    def _fake_report(self):
        return {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "load_generated_resolver_provenance_records": [
                        {
                            "document_id": "RATECON_001",
                            "field": "load_number",
                            "stage": "generated",
                            "candidate_id": "cand-load-1",
                            "candidate_value": "LOAD12345",
                            "source": "table_key_value_row",
                            "parser_name": "load_identifier",
                            "pairing_method": "same_row",
                            "page_number": "1",
                            "line_index": "5",
                        },
                        {
                            "document_id": "RATECON_001",
                            "field": "load_number",
                            "stage": "adapter_input",
                            "candidate_id": "cand-load-1",
                            "candidate_value": "LOAD12345",
                            "source": "table_key_value_row",
                            "parser_name": "load_identifier",
                            "pairing_method": "same_row",
                            "page_number": "1",
                            "line_index": "5",
                        },
                        {
                            "document_id": "RATECON_001",
                            "field": "load_number",
                            "stage": "adapter_output",
                            "candidate_id": "cand-load-1",
                            "candidate_value": "LOAD12345",
                            "source": "table_key_value_row",
                            "parser_name": "load_identifier",
                            "pairing_method": "same_row",
                            "page_number": "1",
                            "line_index": "5",
                        },
                        {
                            "document_id": "RATECON_001",
                            "field": "load_number",
                            "stage": "resolver",
                            "candidate_id": "cand-load-1",
                            "candidate_value": "LOAD12345",
                            "source": "table_key_value_row",
                            "parser_name": "load_identifier",
                            "pairing_method": "same_row",
                            "page_number": "1",
                            "line_index": "5",
                            "selected": True,
                        },
                    ],
                }
            ],
            "aggregate": {},
            "document_count": 1,
        }

    def test_flag_is_absent_by_default_and_safe_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / ".local_outputs" / "private_ratecon_measurement"
            input_dir.mkdir()
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=self._fake_report(),
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            str(input_dir),
                            "--confirm-private-local-run",
                            "--output-dir",
                            str(output_dir),
                        ]
                    )
            sidecar_path = output_dir / "load_generated_resolver_provenance_summary.json"

        self.assertEqual(exit_code, 0)
        self.assertFalse(sidecar_path.exists())

    def test_explicit_flag_writes_redacted_local_only_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / ".local_outputs" / "private_ratecon_measurement"
            input_dir.mkdir()
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=self._fake_report(),
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            str(input_dir),
                            "--confirm-private-local-run",
                            "--output-dir",
                            str(output_dir),
                            "--write-load-generated-resolver-provenance-sidecars",
                        ]
                    )
            summary_path = output_dir / "load_generated_resolver_provenance_summary.json"
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("load_generated_resolver_provenance_sidecars_written", console_output)
        self.assertEqual(1, payload["summary"]["generated_candidate_count"])
        self.assertFalse(payload["summary"]["private_values_included"])
        self.assertTrue(payload["summary"]["values_redacted"])
        self.assertNotIn("LOAD12345", json.dumps(payload))
        self.assertFalse(payload["summary"]["pdf_processing_attempted"])
        self.assertFalse(payload["summary"]["ocr_attempted"])
        self.assertFalse(payload["summary"]["google_called"])
        self.assertFalse(payload["summary"]["model_or_cloud_called"])


if __name__ == "__main__":
    unittest.main()
