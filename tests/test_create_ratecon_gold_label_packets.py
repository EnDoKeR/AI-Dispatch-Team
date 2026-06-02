import json
import tempfile
from pathlib import Path
import unittest

from scripts.create_ratecon_gold_label_packets import create_packets


class CreateRateconGoldLabelPacketsTests(unittest.TestCase):
    def _write_audit(self, directory):
        audit = Path(directory) / "audit.jsonl"
        record = {
            "document_id": "DOC-1",
            "file_hash": "hash123",
            "file_name": "private.pdf",
            "legacy": {
                "load_number": "PRIVATELOAD123",
                "pickup_count": 1,
                "delivery_count": 1,
            },
            "shadow": {
                "success": True,
                "needs_review": True,
                "resolved_fields": {
                    "load_number": {
                        "value": "PRIVATELOAD123",
                        "confidence": 0.84,
                        "source": "native_layout",
                        "candidate_count": 1,
                        "needs_review": False,
                        "review_reasons": [],
                        "evidence_text": "PRIVATE EVIDENCE",
                    }
                },
                "review_gate_trace": {"needs_review": True},
            },
            "triage": {"pdf_type": "born_digital"},
            "candidate_summary": {
                "resolver_selection_summary": {},
                "candidate_quality_summary": {},
            },
            "failure_attribution": {"codes": ["NEEDS_HUMAN_REVIEW"]},
        }
        audit.write_text(json.dumps(record) + "\n", encoding="utf-8")
        summary = Path(directory) / "summary.json"
        summary.write_text("{}", encoding="utf-8")
        return audit, summary

    def test_create_packets_redacts_private_values_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit, summary = self._write_audit(tmp)
            output = Path(tmp) / "packets"

            result = create_packets(
                audit_path=audit,
                summary_path=summary,
                output_dir=output,
                allow_custom_output_dir=True,
            )

            self.assertEqual(result["packet_count"], 1)
            manifest = output / "ratecon_gold_label_packet_manifest.json"
            self.assertTrue(manifest.exists())
            packet_text = (output / result["packet_files"][0]).read_text(encoding="utf-8")
            self.assertNotIn("PRIVATELOAD123", packet_text)
            self.assertNotIn("PRIVATE EVIDENCE", packet_text)
            self.assertIn("gold_label_template", packet_text)

    def test_create_packets_can_include_private_values_explicitly(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit, summary = self._write_audit(tmp)
            output = Path(tmp) / "packets"

            result = create_packets(
                audit_path=audit,
                summary_path=summary,
                output_dir=output,
                include_private_values=True,
                allow_custom_output_dir=True,
            )

            packet_text = (output / result["packet_files"][0]).read_text(encoding="utf-8")
            self.assertIn("PRIVATELOAD123", packet_text)
            self.assertNotIn("PRIVATE EVIDENCE", packet_text)


if __name__ == "__main__":
    unittest.main()
