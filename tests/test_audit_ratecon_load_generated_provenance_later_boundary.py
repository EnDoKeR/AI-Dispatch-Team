import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_ratecon_load_generated_provenance_later_boundary.py"


class AuditRateconLoadGeneratedProvenanceLaterBoundaryTests(unittest.TestCase):
    def _output_dir(self, name: str) -> Path:
        (ROOT / ".local_outputs").mkdir(exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=name, dir=ROOT / ".local_outputs"))

    def test_refuses_without_confirm_flag(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo-root",
                str(ROOT),
                "--output-dir",
                str(self._output_dir("boundary_audit_no_confirm_")),
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

    def test_static_audit_outputs_boundary_fields(self):
        output_dir = self._output_dir("boundary_audit_")
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
            (output_dir / "load_generated_provenance_later_boundary_summary.json").read_text(
                encoding="utf-8"
            )
        )
        with (output_dir / "load_generated_provenance_boundary_fields.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            fields = [row["field_name"] for row in csv.DictReader(handle)]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(summary["module_count"], 0)
        self.assertGreater(summary["symbol_count"], 0)
        self.assertIn("candidate_id", fields)
        self.assertIn("pairing_method", fields)
        self.assertFalse(summary["private_paths_read"])
        self.assertFalse(summary["local_outputs_read"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["google_called"])
        self.assertFalse(summary["model_or_cloud_called"])


if __name__ == "__main__":
    unittest.main()
