import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts import audit_ratecon_ocr_ownership_status as audit_script


class RateconOcrOwnershipStatusAuditTests(unittest.TestCase):
    def _make_repo(self):
        temp = tempfile.TemporaryDirectory()
        repo = Path(temp.name)
        (repo / "app" / "document_ai" / "measurement_cli").mkdir(parents=True)
        (repo / "scripts").mkdir()
        (repo / "tests").mkdir()
        (repo / "docs").mkdir()
        (repo / ".local_outputs").mkdir()
        (repo / "data" / "private_ratecons").mkdir(parents=True)
        sentinel = repo / "executed.txt"

        self._write(
            repo / "app" / "document_ai" / "ocr_provider_contract.py",
            '"""Optional local OCR provider contract."""\n'
            "OCR_PROVIDER_NONE = 'none'\n"
            "def safe_ocr_provider_summary(result):\n"
            "    return {'raw_text_included': False, 'ocr_text_page_count': 0}\n",
        )
        self._write(
            repo / "app" / "document_ai" / "tesseract_ocr_provider.py",
            '"""Optional local Tesseract OCR provider for shadow diagnostics."""\n'
            "from importlib import import_module\n"
            "from app.document_ai.ocr_provider_contract import safe_ocr_provider_summary\n"
            f"Path = __import__('pathlib').Path\n"
            f"Path(r'{sentinel.as_posix()}').write_text('executed')\n"
            "def _safe_import(module_name):\n"
            "    return import_module(module_name)\n"
            "def check_tesseract_ocr_dependencies():\n"
            "    return {'pytesseract_installed': _safe_import('pytesseract') is not None}\n",
        )
        self._write(
            repo / "app" / "document_ai" / "ocr_stop_geometry_assembler.py",
            '"""Experimental shadow OCR geometry stop diagnostics."""\n'
            "from app.document_ai.ocr_provider_contract import safe_ocr_provider_summary\n"
            "GENERATOR = 'ocr_stop_geometry_assembler'\n",
        )
        self._write(
            repo / "app" / "document_ai" / "ocr_stop_table_reconstructor.py",
            "SOURCE = 'ocr_geometry_column'\n",
        )
        self._write(
            repo / "app" / "document_ai" / "ratecon_ocr_candidate_policy.py",
            "OCR_CANDIDATE_POLICIES = {'baseline': {}}\n",
        )
        self._write(
            repo
            / "app"
            / "document_ai"
            / "measurement_cli"
            / "ratecon_private_args.py",
            "def build_parser(parser):\n"
            "    parser.add_argument('--ratecon-shadow-ocr-provider', default='none', choices=['none', 'auto', 'tesseract'])\n"
            "    parser.add_argument('--strict-ratecon-shadow-ocr', action='store_true')\n",
        )
        self._write(
            repo / "scripts" / "run_private_ratecon_measurement.py",
            "from app.document_ai.measurement_cli.ratecon_private_args import build_parser\n"
            "def main():\n"
            "    return 0\n",
        )
        self._write(
            repo / "scripts" / "check_ratecon_ocr_dependencies.py",
            "from app.document_ai.tesseract_ocr_provider import check_tesseract_ocr_dependencies\n",
        )
        self._write(
            repo / "tests" / "test_ocr_shadow.py",
            "from app.document_ai.ocr_provider_contract import safe_ocr_provider_summary\n",
        )
        self._write(repo / "docs" / "ocr.md", "OCR production path is not implemented.\n")
        self._write(
            repo / ".local_outputs" / "private.txt",
            "SENTINEL_PRIVATE_VALUE",
        )
        self._write(
            repo / "data" / "private_ratecons" / "private.pdf",
            "SENTINEL_PRIVATE_VALUE",
        )
        return temp, repo, sentinel

    def _write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _run_audit(self, repo, output_dir=None):
        output_dir = output_dir or repo / ".local_outputs" / "ocr_audit"
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

    def test_writes_expected_outputs_and_detects_ocr_inventory(self):
        temp, repo, sentinel = self._make_repo()
        with temp:
            output_dir, stdout = self._run_audit(repo)
            self.assertIn("RateCon OCR ownership/status audit", stdout)
            self.assertFalse(sentinel.exists(), "fixture OCR module must not execute")
            self.assertEqual(
                {
                    "ocr_ownership_status_summary.json",
                    "ocr_ownership_status_report.md",
                    "ocr_modules.csv",
                    "ocr_import_edges.csv",
                    "ocr_cli_flags.csv",
                    "ocr_dependency_findings.csv",
                    "ocr_status_recommendations.csv",
                    "ocr_risk_findings.csv",
                },
                {path.name for path in output_dir.iterdir()},
            )

            summary = json.loads(
                (output_dir / "ocr_ownership_status_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            module_paths = {row["module_path"] for row in summary["modules"]}
            self.assertIn("app/document_ai/ocr_provider_contract.py", module_paths)
            self.assertIn("app/document_ai/tesseract_ocr_provider.py", module_paths)
            self.assertIn(
                "app/document_ai/ocr_stop_geometry_assembler.py",
                module_paths,
            )
            self.assertIn(
                "app/document_ai/measurement_cli/ratecon_private_args.py",
                module_paths,
            )
            flags = {row["flag"] for row in summary["cli_flags"]}
            self.assertIn("--ratecon-shadow-ocr-provider", flags)
            self.assertIn("--strict-ratecon-shadow-ocr", flags)
            self.assertFalse(summary["production_ocr_path_implemented"])
            self.assertTrue(summary["ocr_disabled_by_default"])
            self.assertFalse(summary["ocr_dependencies_mandatory"])

    def test_detects_import_edges_optional_dependency_and_status(self):
        temp, repo, _sentinel = self._make_repo()
        with temp:
            output_dir, _stdout = self._run_audit(repo)
            summary = json.loads(
                (output_dir / "ocr_ownership_status_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            edges = {
                (row["importer_path"], row["imported_path"])
                for row in summary["import_edges"]
            }
            self.assertIn(
                (
                    "app/document_ai/tesseract_ocr_provider.py",
                    "app/document_ai/ocr_provider_contract.py",
                ),
                edges,
            )
            modules = {row["module_path"]: row for row in summary["modules"]}
            tesseract = modules["app/document_ai/tesseract_ocr_provider.py"]
            self.assertEqual(tesseract["dependency_status"], "optional_dynamic_import")
            self.assertEqual(
                tesseract["status_recommendation"],
                "experimental_shadow_local",
            )
            self.assertEqual(tesseract["risk"], "medium")
            contract = modules["app/document_ai/ocr_provider_contract.py"]
            self.assertEqual(contract["status_recommendation"], "active_shadow_local")

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
                (output_dir / "ocr_ownership_status_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            safety = summary["safety"]
            self.assertFalse(safety["project_modules_imported"])
            self.assertFalse(safety["ocr_attempted"])
            self.assertFalse(safety["tesseract_dependency_checked"])
            self.assertFalse(safety["pdf_processing_attempted"])
            self.assertFalse(safety["local_outputs_read"])
            self.assertFalse(safety["private_ratecons_read"])
            self.assertFalse(safety["google_called"])
            self.assertFalse(safety["model_or_cloud_called"])


if __name__ == "__main__":
    unittest.main()
