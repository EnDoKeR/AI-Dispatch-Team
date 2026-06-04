import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import audit_ratecon_rate_ranking_penalty_ownership as audit_script


root = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class RateconRateRankingPenaltyOwnershipTests(unittest.TestCase):
    def _fixture_repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        _write(
            repo / "app" / "document_ai" / "field_candidate_resolver.py",
            "\n".join(
                [
                    "RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1 = 'money_abstain_v1'",
                    "TOTAL_RATE_BOOST = 0.06",
                    "LINE_ITEM_RATE_PENALTY = -0.25",
                    "def score_rate_candidate(candidate):",
                    "    return candidate.get('confidence', 0) + TOTAL_RATE_BOOST",
                    "def _profile_adjustments(field_name, candidate, ranking_profile):",
                    "    return [('line_item_only_penalty', LINE_ITEM_RATE_PENALTY)]",
                    "",
                ]
            ),
        )
        _write(
            repo / "app" / "document_ai" / "ratecon_rate_money_safety.py",
            "RATE_SELECTION_ABSTAIN = 'abstain'\n"
            "def apply_rate_money_abstention_profile_to_candidates(candidates):\n"
            "    return candidates\n",
        )
        _write(
            repo / "app" / "document_ai" / "rate_candidate_forensics.py",
            "RATE_FORENSICS_SELECTED_WRONG_CONTEXT = 'selected_wrong_money_context'\n",
        )
        _write(
            repo / "scripts" / "evaluate_ratecon_against_gold.py",
            "def report():\n"
            "    return 'gold_total_in_candidates_not_selected'\n",
        )
        _write(
            repo / ".local_outputs" / "ignored.py",
            "IGNORED_RATE_PENALTY = -99\n",
        )
        _write(
            repo / "data" / "private_ratecons" / "ignored.py",
            "IGNORED_RATE_PENALTY = -99\n",
        )
        return repo

    def test_refuses_without_confirm_flag(self):
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/audit_ratecon_rate_ranking_penalty_ownership.py",
                "--repo-root",
                ".",
                "--output-dir",
                ".local_outputs/rate_ranking_test",
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
                    str(root / "scripts" / "audit_ratecon_rate_ranking_penalty_ownership.py"),
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

    def test_static_audit_detects_ranking_modules_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = self._fixture_repo(tmp_path)
            output_dir = repo / ".local_outputs" / "rate_ranking_audit"
            summary = audit_script.analyze_rate_ranking_penalty_ownership(repo)
            audit_script.write_audit_outputs(output_dir, summary)
            payload = json.loads(
                (output_dir / "rate_ranking_penalty_ownership_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            output_exists = {
                filename: (output_dir / filename).exists()
                for filename in (
                    "rate_ranking_penalty_ownership_report.md",
                    "rate_ranking_modules.csv",
                    "rate_ranking_import_edges.csv",
                    "rate_ranking_symbols.csv",
                    "rate_ranking_penalty_constants.csv",
                    "rate_ranking_status_recommendations.csv",
                    "rate_ranking_risk_findings.csv",
                )
            }

        module_paths = {row["module_path"] for row in payload["modules"]}
        symbol_names = {row["symbol_name"] for row in payload["symbols"]}
        self.assertIn("app/document_ai/field_candidate_resolver.py", module_paths)
        self.assertIn("scripts/evaluate_ratecon_against_gold.py", module_paths)
        self.assertIn("RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1", symbol_names)
        self.assertIn("LINE_ITEM_RATE_PENALTY", symbol_names)
        self.assertGreaterEqual(payload["penalty_constant_count"], 2)
        self.assertEqual(output_exists, {filename: True for filename in output_exists})

    def test_static_audit_ignores_local_outputs_and_private_ratecons(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(Path(tmp))
            summary = audit_script.analyze_rate_ranking_penalty_ownership(repo)

        paths = {row["module_path"] for row in summary["symbols"]}
        self.assertNotIn(".local_outputs/ignored.py", paths)
        self.assertNotIn("data/private_ratecons/ignored.py", paths)

    def test_script_runs_against_real_repo_without_runtime_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(".local_outputs") / "test_rate_ranking_penalty_ownership_real"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/audit_ratecon_rate_ranking_penalty_ownership.py",
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
