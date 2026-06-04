import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts import audit_ratecon_rate_money_safety_ownership as audit_script


class RateconRateMoneySafetyOwnershipAuditTests(unittest.TestCase):
    def _write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _make_repo(self):
        temp = tempfile.TemporaryDirectory()
        repo = Path(temp.name)
        (repo / "app" / "document_ai").mkdir(parents=True)
        (repo / "scripts").mkdir()
        (repo / ".local_outputs").mkdir()
        (repo / "data" / "private_ratecons").mkdir(parents=True)
        sentinel = repo / "executed.txt"

        self._write(
            repo / "app" / "document_ai" / "ratecon_rate_money_safety.py",
            "from pathlib import Path\n"
            f"Path(r'{sentinel.as_posix()}').write_text('executed')\n"
            "RATE_MONEY_SAFE = 'safe'\n"
            "RATE_MONEY_UNSAFE = 'unsafe'\n"
            "MONEY_CONTEXT_TOTAL_CARRIER_PAY = 'total_carrier_pay'\n"
            "MONEY_CONTEXT_ACCESSORIAL = 'accessorial'\n"
            "def enrich_rate_money_safety(candidate):\n"
            "    return candidate\n",
        )
        self._write(
            repo / "app" / "document_ai" / "field_candidate_resolver.py",
            "from app.document_ai.ratecon_rate_money_safety import RATE_MONEY_SAFE\n"
            "FIELD_TOTAL_CARRIER_RATE = 'total_carrier_rate'\n"
            "RATE_NEGATIVE_LABELS = ('quickpay', 'detention')\n"
            "def resolve_rate_candidate(candidate):\n"
            "    return RATE_MONEY_SAFE\n",
        )
        self._write(
            repo / "app" / "document_ai" / "rate_candidate_forensics.py",
            "RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY = 'main_total_carrier_pay'\n"
            "RATE_CONFLICT_UNKNOWN = 'unknown'\n"
            "def classify_rate_candidate_category(candidate):\n"
            "    return RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY\n",
        )
        self._write(
            repo / "app" / "document_ai" / "rate_conflict_audit.py",
            "RATE_AUDIT_UNKNOWN = 'unknown'\n",
        )
        self._write(
            repo / ".local_outputs" / "private.txt",
            "SENTINEL_PRIVATE_VALUE",
        )
        self._write(
            repo / "data" / "private_ratecons" / "private.pdf",
            "SENTINEL_PRIVATE_VALUE",
        )
        return temp, repo, sentinel

    def _run_audit(self, repo, output_dir=None):
        output_dir = output_dir or repo / ".local_outputs" / "rate_money_audit"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = audit_script.main(
                [
                    "--repo-root",
                    str(repo),
                    "--output-dir",
                    str(output_dir),
                    "--confirm-local-audit-run",
                ]
            )
        self.assertEqual(result, 0)
        return output_dir, stdout.getvalue()

    def test_refuses_without_confirm_flag(self):
        with self.assertRaises(SystemExit) as raised:
            audit_script.main(["--repo-root", "."])
        self.assertEqual(raised.exception.code, 2)

    def test_refuses_output_outside_local_outputs(self):
        temp, repo, _sentinel = self._make_repo()
        with temp:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = audit_script.main(
                    [
                        "--repo-root",
                        str(repo),
                        "--output-dir",
                        str(repo / "audit"),
                        "--confirm-local-audit-run",
                    ]
                )
            self.assertEqual(result, 2)
            self.assertIn("Output directory must be under .local_outputs", stdout.getvalue())

    def test_writes_expected_outputs_and_detects_rate_money_inventory(self):
        temp, repo, sentinel = self._make_repo()
        with temp:
            output_dir, stdout = self._run_audit(repo)

            self.assertIn("RateCon rate/money safety ownership audit", stdout)
            self.assertFalse(sentinel.exists(), "fixture module must not execute")
            self.assertEqual(
                {
                    "rate_money_safety_ownership_summary.json",
                    "rate_money_safety_ownership_report.md",
                    "rate_money_modules.csv",
                    "rate_money_import_edges.csv",
                    "rate_money_symbols.csv",
                    "rate_money_duplicate_constants.csv",
                    "rate_money_status_recommendations.csv",
                    "rate_money_risk_findings.csv",
                },
                {path.name for path in output_dir.iterdir()},
            )

            summary = json.loads(
                (output_dir / "rate_money_safety_ownership_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            module_paths = {row["module_path"] for row in summary["modules"]}
            self.assertIn("app/document_ai/ratecon_rate_money_safety.py", module_paths)
            self.assertIn("app/document_ai/field_candidate_resolver.py", module_paths)
            self.assertIn("app/document_ai/rate_candidate_forensics.py", module_paths)
            self.assertIn("app/document_ai/rate_conflict_audit.py", module_paths)

            modules = {row["module_path"]: row for row in summary["modules"]}
            self.assertEqual(
                "canonical_rate_money_safety",
                modules["app/document_ai/ratecon_rate_money_safety.py"][
                    "canonical_owner_recommendation"
                ],
            )
            self.assertEqual(
                "resolver_consumer",
                modules["app/document_ai/field_candidate_resolver.py"][
                    "canonical_owner_recommendation"
                ],
            )
            self.assertGreater(summary["symbol_count"], 0)
            self.assertGreater(summary["duplicate_constant_count"], 0)

    def test_ignores_private_dirs_and_records_safety_no_execution(self):
        temp, repo, _sentinel = self._make_repo()
        with temp:
            output_dir, _stdout = self._run_audit(repo)
            for path in output_dir.iterdir():
                self.assertNotIn(
                    "SENTINEL_PRIVATE_VALUE",
                    path.read_text(encoding="utf-8"),
                    msg=f"private value leaked into {path}",
                )
            summary = json.loads(
                (output_dir / "rate_money_safety_ownership_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            safety = summary["safety"]
            self.assertFalse(safety["project_modules_imported"])
            self.assertFalse(safety["extraction_executed"])
            self.assertFalse(safety["resolver_executed"])
            self.assertFalse(safety["pdf_processing_attempted"])
            self.assertFalse(safety["ocr_attempted"])
            self.assertFalse(safety["local_outputs_read"])
            self.assertFalse(safety["private_ratecons_read"])
            self.assertFalse(safety["google_called"])
            self.assertFalse(safety["model_or_cloud_called"])


if __name__ == "__main__":
    unittest.main()
