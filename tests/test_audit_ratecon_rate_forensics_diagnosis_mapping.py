import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import audit_ratecon_rate_forensics_diagnosis_mapping as audit_script


root = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class RateconRateForensicsDiagnosisMappingAuditTests(unittest.TestCase):
    def _fixture_repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        _write(
            repo / "app" / "document_ai" / "rate_candidate_forensics.py",
            "\n".join(
                [
                    "RATE_FORENSICS_SELECTED_WRONG_CONTEXT = 'selected_wrong_money_context'",
                    "def normalize_rate_conflict_reason(value):",
                    "    return value or 'unknown'",
                    "",
                ]
            ),
        )
        _write(
            repo / "app" / "document_ai" / "rate_conflict_audit.py",
            "RATE_AUDIT_UNKNOWN = 'unknown'\n",
        )
        _write(
            repo / "app" / "document_ai" / "ratecon_gold_labels.py",
            "def _classify_residual_wrong_rate(row, record, gold_field, index):\n"
            "    return 'selected_safe_total_but_gold_differs'\n",
        )
        _write(
            repo / "scripts" / "evaluate_ratecon_against_gold.py",
            "def summarize(summary):\n"
            "    return summary.get('diagnosis_counts', {})\n",
        )
        _write(
            repo / ".local_outputs" / "ignored.py",
            "IGNORED_DIAGNOSIS = 'private'\n",
        )
        _write(
            repo / "data" / "private_ratecons" / "ignored.py",
            "IGNORED_DIAGNOSIS = 'private'\n",
        )
        return repo

    def test_refuses_without_confirm_flag(self):
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/audit_ratecon_rate_forensics_diagnosis_mapping.py",
                "--repo-root",
                ".",
                "--output-dir",
                ".local_outputs/rate_forensics_diagnosis_test",
            ],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(2, completed.returncode)
        self.assertIn("--confirm-local-audit-run is required", completed.stdout)

    def test_refuses_output_outside_local_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(Path(tmp))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(
                        root
                        / "scripts"
                        / "audit_ratecon_rate_forensics_diagnosis_mapping.py"
                    ),
                    "--repo-root",
                    str(repo),
                    "--output-dir",
                    str(Path(tmp) / "not_local_outputs"),
                    "--confirm-local-audit-run",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(0, completed.returncode)
        self.assertIn("Output directory must be under .local_outputs", completed.stdout)

    def test_static_audit_detects_diagnosis_modules_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(Path(tmp))
            output_dir = repo / ".local_outputs" / "rate_forensics_diagnosis_audit"
            summary = audit_script.analyze_rate_forensics_diagnosis_mapping(repo)
            audit_script.write_audit_outputs(output_dir, summary)
            payload = json.loads(
                (
                    output_dir / "rate_forensics_diagnosis_mapping_summary.json"
                ).read_text(encoding="utf-8")
            )
            output_exists = {
                filename: (output_dir / filename).exists()
                for filename in (
                    "rate_forensics_diagnosis_mapping_report.md",
                    "rate_forensics_diagnosis_modules.csv",
                    "rate_forensics_diagnosis_symbols.csv",
                    "rate_forensics_diagnosis_constants.csv",
                    "rate_forensics_diagnosis_recommendations.csv",
                    "rate_forensics_diagnosis_risk_findings.csv",
                )
            }

        module_paths = {row["module_path"] for row in payload["modules"]}
        symbol_names = {row["symbol_name"] for row in payload["symbols"]}
        self.assertIn("app/document_ai/rate_candidate_forensics.py", module_paths)
        self.assertIn("app/document_ai/ratecon_gold_labels.py", module_paths)
        self.assertIn("RATE_FORENSICS_SELECTED_WRONG_CONTEXT", symbol_names)
        self.assertIn("_classify_residual_wrong_rate", symbol_names)
        self.assertGreaterEqual(payload["diagnosis_constant_count"], 1)
        self.assertEqual(output_exists, {filename: True for filename in output_exists})

    def test_static_audit_ignores_local_outputs_and_private_ratecons(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(Path(tmp))
            summary = audit_script.analyze_rate_forensics_diagnosis_mapping(repo)

        paths = {row["module_path"] for row in summary["symbols"]}
        self.assertNotIn(".local_outputs/ignored.py", paths)
        self.assertNotIn("data/private_ratecons/ignored.py", paths)

    def test_script_runs_against_real_repo_without_runtime_side_effects(self):
        output_dir = Path(".local_outputs") / "test_rate_forensics_diagnosis_real"
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/audit_ratecon_rate_forensics_diagnosis_mapping.py",
                "--repo-root",
                ".",
                "--output-dir",
                str(output_dir),
                "--confirm-local-audit-run",
            ],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("pdf_processing_attempted: False", completed.stdout)
        self.assertIn("ocr_attempted: False", completed.stdout)
        self.assertIn("google_called: False", completed.stdout)
        self.assertIn("model_or_cloud_called: False", completed.stdout)


if __name__ == "__main__":
    unittest.main()
