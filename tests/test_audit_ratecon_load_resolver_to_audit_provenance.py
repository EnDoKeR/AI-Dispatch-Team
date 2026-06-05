import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_ratecon_load_resolver_to_audit_provenance.py"


class AuditRateconLoadResolverToAuditProvenanceTests(unittest.TestCase):
    def _repo_local_output(self, name: str) -> Path:
        root = ROOT / ".local_outputs"
        root.mkdir(exist_ok=True)
        path = Path(tempfile.mkdtemp(prefix=name, dir=root))
        return path

    def test_refuses_without_confirm_flag(self):
        output_dir = self._repo_local_output("resolver_to_audit_no_confirm_")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo-root",
                str(ROOT),
                "--output-dir",
                str(output_dir),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        shutil.rmtree(output_dir, ignore_errors=True)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--confirm-local-audit-run is required", result.stderr)

    def test_static_audit_outputs_expected_files(self):
        output_dir = self._repo_local_output("resolver_to_audit_audit_")
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
            (output_dir / "load_resolver_to_audit_provenance_summary.json").read_text(
                encoding="utf-8"
            )
        )
        files = {
            name: (output_dir / name).exists()
            for name in (
                "load_resolver_to_audit_provenance_summary.json",
                "load_resolver_to_audit_provenance_report.md",
                "load_resolver_to_audit_modules.csv",
                "load_resolver_to_audit_symbols.csv",
                "load_resolver_to_audit_field_map.csv",
                "load_resolver_to_audit_risk_findings.csv",
            )
        }
        shutil.rmtree(output_dir, ignore_errors=True)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(files, {name: True for name in files})
        self.assertGreater(summary["module_count"], 0)
        self.assertFalse(summary["private_paths_read"])
        self.assertFalse(summary["local_outputs_read"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["google_called"])
        self.assertFalse(summary["model_or_cloud_called"])


if __name__ == "__main__":
    unittest.main()
