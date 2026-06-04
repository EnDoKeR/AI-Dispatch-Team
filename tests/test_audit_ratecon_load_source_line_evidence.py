import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_ratecon_load_source_line_evidence.py"


class AuditRateconLoadSourceLineEvidenceTests(unittest.TestCase):
    def test_refuses_without_confirm_flag(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(ROOT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("--confirm-local-audit-run is required", result.stderr)

    def test_refuses_output_outside_local_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo-root",
                    str(ROOT),
                    "--output-dir",
                    str(Path(tmp) / "outside"),
                    "--confirm-local-audit-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Output directory must be under .local_outputs", result.stderr)

    def test_static_audit_writes_outputs_and_detects_source_line_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = ROOT / ".local_outputs" / f"test_source_line_audit_{Path(tmp).name}"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo-root",
                    str(ROOT),
                    "--output-dir",
                    str(output_dir),
                    "--confirm-local-audit-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            summary = json.loads(
                (output_dir / "load_source_line_evidence_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            outputs = {
                name: (output_dir / name).exists()
                for name in (
                    "load_source_line_evidence_summary.json",
                    "load_source_line_evidence_report.md",
                    "load_source_line_modules.csv",
                    "load_source_line_symbols.csv",
                    "load_source_line_pairing_reasons.csv",
                    "load_source_line_risk_findings.csv",
                )
            }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(summary["module_count"], 0)
        self.assertGreater(summary["symbol_count"], 0)
        self.assertGreater(summary["reason_constant_count"], 0)
        self.assertIn("source_line_audit_owner", summary["recommendation_counts"])
        self.assertTrue(summary["static_analysis_only"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["google_called"])
        self.assertFalse(summary["model_or_cloud_called"])
        self.assertEqual(outputs, {name: True for name in outputs})


if __name__ == "__main__":
    unittest.main()
