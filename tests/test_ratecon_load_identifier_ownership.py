import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = ROOT / "scripts" / "audit_ratecon_load_identifier_ownership.py"


class RateconLoadIdentifierOwnershipTests(unittest.TestCase):
    def test_ownership_docs_exist_and_define_boundaries(self):
        doc = (ROOT / "docs" / "ratecon_load_identifier_ownership_v1.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("load_identifier_candidates.py", doc)
        self.assertIn("field_candidate_generators.py", doc)
        self.assertIn("field_candidate_resolver.py", doc)
        self.assertIn("load_identity_forensics.py", doc)
        self.assertIn("changes no selected load-number behavior", doc)

    def test_static_audit_refuses_without_confirm_flag(self):
        result = subprocess.run(
            [sys.executable, str(AUDIT_SCRIPT), "--repo-root", str(ROOT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("--confirm-local-audit-run is required", result.stderr)

    def test_static_audit_writes_local_only_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = ROOT / ".local_outputs" / f"test_load_identifier_audit_{Path(tmp).name}"
            result = subprocess.run(
                [
                    sys.executable,
                    str(AUDIT_SCRIPT),
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
                (output_dir / "load_identifier_ownership_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            expected_outputs = {
                filename: (output_dir / filename).exists()
                for filename in (
                    "load_identifier_ownership_summary.json",
                    "load_identifier_ownership_report.md",
                    "load_identifier_modules.csv",
                    "load_identifier_symbols.csv",
                    "load_identifier_duplicate_constants.csv",
                    "load_identifier_recommendations.csv",
                    "load_identifier_risk_findings.csv",
                )
            }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(summary["module_count"], 5)
        self.assertIn(
            "canonical_load_identifier_candidate_owner",
            summary["status_recommendation_counts"],
        )
        self.assertTrue(summary["static_analysis_only"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["google_called"])
        self.assertFalse(summary["model_or_cloud_called"])
        self.assertFalse(summary["private_measurement_run"])
        self.assertEqual(expected_outputs, {name: True for name in expected_outputs})

    def test_static_audit_refuses_output_outside_local_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(AUDIT_SCRIPT),
                    "--repo-root",
                    str(ROOT),
                    "--output-dir",
                    str(Path(tmp) / "not_local_outputs"),
                    "--confirm-local-audit-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Output directory must be under .local_outputs", result.stderr)


if __name__ == "__main__":
    unittest.main()
