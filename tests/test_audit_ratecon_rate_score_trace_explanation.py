import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import audit_ratecon_rate_score_trace_explanation as audit_script


root = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class RateconRateScoreTraceExplanationAuditTests(unittest.TestCase):
    def _fixture_repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        _write(
            repo / "app" / "document_ai" / "field_candidate_resolver.py",
            "\n".join(
                [
                    "REJECT_LOWER_CONFIDENCE = 'lower_confidence'",
                    "def _apply_score_trace(candidate, ranking_profile, adjustments):",
                    "    candidate['metadata'] = {'ranking_adjustments': adjustments}",
                    "def _not_selected_reason(field_name, candidate):",
                    "    return REJECT_LOWER_CONFIDENCE",
                    "def build_resolver_decision_traces(candidates):",
                    "    return {'total_carrier_rate': {'decision_status': 'selected'}}",
                    "",
                ]
            ),
        )
        _write(
            repo / "app" / "document_ai" / "ratecon_rate_money_safety.py",
            "def classify_money_context(text):\n"
            "    return {'money_context': 'total_carrier_pay'}\n",
        )
        _write(
            repo / "app" / "document_ai" / "rate_candidate_forensics.py",
            "RATE_DIAGNOSIS_REASON = 'selected_safe_total_but_gold_differs'\n",
        )
        _write(
            repo / "scripts" / "evaluate_ratecon_against_gold.py",
            "def summarize(trace):\n"
            "    return trace.get('resolver_decision_traces', {})\n",
        )
        _write(
            repo / ".local_outputs" / "ignored.py",
            "IGNORED_TRACE_REASON = 'private'\n",
        )
        _write(
            repo / "data" / "private_ratecons" / "ignored.py",
            "IGNORED_TRACE_REASON = 'private'\n",
        )
        return repo

    def test_refuses_without_confirm_flag(self):
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/audit_ratecon_rate_score_trace_explanation.py",
                "--repo-root",
                ".",
                "--output-dir",
                ".local_outputs/rate_score_trace_test",
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
                    str(root / "scripts" / "audit_ratecon_rate_score_trace_explanation.py"),
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

    def test_static_audit_detects_trace_modules_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(Path(tmp))
            output_dir = repo / ".local_outputs" / "rate_score_trace_audit"
            summary = audit_script.analyze_rate_score_trace_explanation(repo)
            audit_script.write_audit_outputs(output_dir, summary)
            payload = json.loads(
                (output_dir / "rate_score_trace_explanation_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            output_exists = {
                filename: (output_dir / filename).exists()
                for filename in (
                    "rate_score_trace_explanation_report.md",
                    "rate_score_trace_modules.csv",
                    "rate_score_trace_symbols.csv",
                    "rate_score_trace_reason_constants.csv",
                    "rate_score_trace_recommendations.csv",
                    "rate_score_trace_risk_findings.csv",
                )
            }

        module_paths = {row["module_path"] for row in payload["modules"]}
        symbol_names = {row["symbol_name"] for row in payload["symbols"]}
        self.assertIn("app/document_ai/field_candidate_resolver.py", module_paths)
        self.assertIn("scripts/evaluate_ratecon_against_gold.py", module_paths)
        self.assertIn("REJECT_LOWER_CONFIDENCE", symbol_names)
        self.assertIn("build_resolver_decision_traces", symbol_names)
        self.assertGreaterEqual(payload["reason_constant_count"], 1)
        self.assertEqual(output_exists, {filename: True for filename in output_exists})

    def test_static_audit_ignores_local_outputs_and_private_ratecons(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(Path(tmp))
            summary = audit_script.analyze_rate_score_trace_explanation(repo)

        paths = {row["module_path"] for row in summary["symbols"]}
        self.assertNotIn(".local_outputs/ignored.py", paths)
        self.assertNotIn("data/private_ratecons/ignored.py", paths)

    def test_script_runs_against_real_repo_without_runtime_side_effects(self):
        output_dir = Path(".local_outputs") / "test_rate_score_trace_explanation_real"
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/audit_ratecon_rate_score_trace_explanation.py",
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
