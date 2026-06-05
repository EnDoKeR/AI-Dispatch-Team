import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_ratecon_load_candidate_adapter_provenance.py"


class AuditRateconLoadCandidateAdapterProvenanceTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path) -> Path:
        return ROOT / ".local_outputs" / f"adapter_provenance_audit_{tmp_path.name}"

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

    def test_static_audit_writes_expected_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = self._output_dir(Path(tmp))
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
                (output_dir / "load_candidate_adapter_provenance_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            outputs = {
                filename: (output_dir / filename).exists()
                for filename in (
                    "load_candidate_adapter_provenance_summary.json",
                    "load_candidate_adapter_provenance_report.md",
                    "load_candidate_adapter_modules.csv",
                    "load_candidate_adapter_symbols.csv",
                    "load_candidate_adapter_field_map.csv",
                    "load_candidate_adapter_risk_findings.csv",
                )
            }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(summary["module_count"], 0)
        self.assertGreater(summary["symbol_count"], 0)
        self.assertGreater(summary["field_map_count"], 0)
        self.assertEqual(0, summary["risk_finding_count"])
        self.assertIn("adapter_boundary_owner", summary["recommendation_counts"])
        self.assertTrue(summary["static_analysis_only"])
        self.assertFalse(summary["project_modules_imported"])
        self.assertFalse(summary["resolver_or_extraction_executed"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["google_called"])
        self.assertFalse(summary["model_or_cloud_called"])
        self.assertFalse(summary["private_measurement_run"])
        self.assertEqual(outputs, {name: True for name in outputs})


if __name__ == "__main__":
    unittest.main()
