import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.analyze_ratecon_shadow_audit import main


class AnalyzeRateConShadowAuditCliTests(unittest.TestCase):
    def test_cli_writes_safe_reports_from_synthetic_audit(self):
        record = {
            "document_id": "RATECON_001",
            "shadow": {
                "success": True,
                "needs_review": True,
                "review_reasons": ["MISSING_CRITICAL_FIELD:load_number"],
            },
            "triage": {"pdf_type": "born_digital", "quality_flags": []},
            "candidate_summary": {
                "candidates_by_field": {"total_carrier_rate": 1},
            },
            "legacy_shadow_comparison": {
                "load_number": "legacy_only",
                "total_carrier_rate": "same",
            },
            "failure_attribution": {
                "primary_suspected_layer": "candidate_generation",
                "codes": ["MISSING_LOAD_NUMBER_CANDIDATE"],
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path = root / "shadow_summary.json"
            audit_path = root / "shadow.jsonl"
            summary_path.write_text('{"documents_processed": 1}', encoding="utf-8")
            audit_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "--summary",
                        str(summary_path),
                        "--audit",
                        str(audit_path),
                        "--output-dir",
                        str(root),
                        "--allow-custom-output-dir",
                        "--top-n",
                        "5",
                    ]
                )
            console = buffer.getvalue()
            report_text = (root / "ratecon_shadow_root_cause_report.md").read_text(
                encoding="utf-8"
            )
            summary = json.loads(
                (root / "ratecon_shadow_root_cause_summary.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("ratecon_shadow_root_cause_analysis_written", console)
        self.assertIn("ratecon_shadow_root_cause_report.md", console)
        self.assertIn("PRIMARY NEXT MOVE", report_text)
        self.assertEqual(summary["documents_processed"], 1)
        self.assertNotIn("FAKE_PRIVATE_VALUE", console + report_text)
        self.assertNotIn(temp_dir, console)


if __name__ == "__main__":
    unittest.main()
