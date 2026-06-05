import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_ratecon_load_source_line_serialization.py"


class AuditRateconLoadSourceLineSerializationTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path) -> Path:
        return ROOT / ".local_outputs" / f"serialization_audit_{tmp_path.name}"

    def test_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo-root",
                    str(ROOT),
                    "--output-dir",
                    str(self._output_dir(Path(tmp))),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
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

    def test_static_audit_detects_serialization_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = self._output_dir(tmp_path)
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
                (output_dir / "load_source_line_serialization_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            outputs = {
                name: (output_dir / name).exists()
                for name in (
                    "load_source_line_serialization_summary.json",
                    "load_source_line_serialization_report.md",
                    "load_source_line_serialization_modules.csv",
                    "load_source_line_serialization_symbols.csv",
                    "load_source_line_serialization_fields.csv",
                    "load_source_line_serialization_risk_findings.csv",
                )
            }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(summary["module_count"], 0)
        self.assertGreater(summary["symbol_count"], 0)
        self.assertGreater(summary["field_count"], 0)
        self.assertEqual(0, summary["risk_finding_count"])
        self.assertTrue(summary["static_analysis_only"])
        self.assertFalse(summary["project_modules_imported"])
        self.assertFalse(summary["resolver_or_extraction_executed"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["google_called"])
        self.assertFalse(summary["model_or_cloud_called"])
        self.assertEqual(outputs, {name: True for name in outputs})


if __name__ == "__main__":
    unittest.main()
