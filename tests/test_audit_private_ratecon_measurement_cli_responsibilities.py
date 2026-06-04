import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts import audit_private_ratecon_measurement_cli_responsibilities as audit_script


class PrivateRateconMeasurementCliResponsibilityAuditTests(unittest.TestCase):
    def _make_repo(self):
        temp = tempfile.TemporaryDirectory()
        repo = Path(temp.name)
        (repo / "scripts").mkdir()
        (repo / ".local_outputs").mkdir()
        (repo / "data" / "private_ratecons").mkdir(parents=True)
        sentinel = repo / "executed.txt"
        script = self._fixture_script(sentinel)
        (repo / "scripts" / "run_private_ratecon_measurement.py").write_text(
            script,
            encoding="utf-8",
        )
        (repo / ".local_outputs" / "should_be_ignored.txt").write_text(
            "SENTINEL_PRIVATE_VALUE",
            encoding="utf-8",
        )
        (repo / "data" / "private_ratecons" / "ignored.pdf").write_text(
            "SENTINEL_PRIVATE_VALUE",
            encoding="utf-8",
        )
        return temp, repo, sentinel, script

    def _fixture_script(self, sentinel):
        return (
            '"""Sanitized fixture CLI."""\n'
            "from pathlib import Path\n"
            "from app.document_ai.broker_template_registry import BrokerTemplateRegistry\n"
            "from app.document_ai.layout_provider_diagnostics import compare_pdfplumber_table_profiles\n"
            "from app.document_ai.measurement_cli.ratecon_private_args import parse_private_ratecon_measurement_args\n"
            "from app.document_ai.measurement_cli.ratecon_private_config import build_private_ratecon_measurement_config\n"
            "from app.document_ai.measurement_cli.ratecon_private_safety import validate_private_ratecon_measurement_config\n"
            "from app.document_ai.measurement_cli.ratecon_private_output_paths import build_private_ratecon_output_paths\n"
            "from app.document_ai.measurement_cli.ratecon_private_report_writers import write_private_ratecon_safe_outputs\n"
            "from app.document_ai.measurement_cli.ratecon_private_review_exports import write_private_ratecon_review_packet_exports\n"
            "from app.document_ai.measurement_cli.ratecon_private_audit_orchestration import run_private_ratecon_audit_exports\n"
            "from app.document_ai.measurement_cli.ratecon_private_review_workbook import write_private_ratecon_review_workbook_if_enabled\n"
            "from app.document_ai.measurement_cli.ratecon_private_google_sync import run_private_ratecon_google_sync_if_enabled\n"
            "from app.document_ai.private_measurement_inputs import discover_private_pdfs, build_safe_aliases\n"
            "from app.document_ai.private_measurement_pipeline import measure_private_ratecon_pdf\n"
            "from app.document_ai.private_measurement_review_export import write_ratecon_review_export\n"
            f"Path(r'{sentinel.as_posix()}').write_text('executed')\n"
            "# TODO: sanitized fixture marker\n"
            "\n"
            "def _load_registry(template_dir):\n"
            "    return BrokerTemplateRegistry.from_directory(template_dir)\n"
            "\n"
            "def build_private_ratecon_measurement_report(input_dir):\n"
            "    pdfs = discover_private_pdfs(input_dir)\n"
            "    aliases = build_safe_aliases(pdfs)\n"
            "    registry = _load_registry('templates')\n"
            "    rows = [measure_private_ratecon_pdf(path, aliases[path], registry) for path in pdfs]\n"
            "    compare_pdfplumber_table_profiles('fixture.pdf')\n"
            "    write_ratecon_review_export(rows, output_dir='.local_outputs/x')\n"
            "    return {'rows': rows, 'aggregate': {}}\n"
            "\n"
            "def format_private_measurement_report(report):\n"
            "    print('safe summary')\n"
            "    return ['safe summary']\n"
            "\n"
            "def main(argv=None):\n"
            "    args = parse_private_ratecon_measurement_args(argv)\n"
            "    config = build_private_ratecon_measurement_config(args)\n"
            "    validate_private_ratecon_measurement_config(config)\n"
            "    output_paths = build_private_ratecon_output_paths(config)\n"
            "    report = build_private_ratecon_measurement_report(args.input_dir)\n"
            "    write_private_ratecon_safe_outputs(report['rows'], report['aggregate'], output_dir=output_paths.output_dir)\n"
            "    write_private_ratecon_review_packet_exports(report['rows'], output_dir=output_paths.output_dir)\n"
            "    write_private_ratecon_review_workbook_if_enabled(report, config, output_paths)\n"
            "    run_private_ratecon_audit_exports(report, config, output_paths)\n"
            "    run_private_ratecon_google_sync_if_enabled(report, config, output_paths)\n"
            "    return 0\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n"
        )

    def _run_audit(self, repo, output_dir=None):
        output_dir = output_dir or repo / ".local_outputs" / "audit"
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
        with self._make_repo()[0] as temp_name:
            repo = Path(temp_name)
            outside = repo / "audit"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = audit_script.main(
                    [
                        "--repo-root",
                        str(repo),
                        "--output-dir",
                        str(outside),
                        "--confirm-local-audit-run",
                    ]
                )
            self.assertEqual(result, 2)
            self.assertIn("Output directory must be under .local_outputs", stdout.getvalue())

    def test_writes_expected_outputs_and_detects_structure(self):
        temp, repo, sentinel, script = self._make_repo()
        with temp:
            output_dir, stdout = self._run_audit(repo)
            self.assertIn("Private RateCon measurement CLI responsibility audit", stdout)
            expected_files = {
                "measurement_cli_responsibility_summary.json",
                "measurement_cli_responsibility_report.md",
                "measurement_cli_responsibility_sections.csv",
                "measurement_cli_remaining_imports.csv",
                "measurement_cli_remaining_direct_calls.csv",
                "measurement_cli_recommendations.csv",
            }
            self.assertEqual(expected_files, {path.name for path in output_dir.iterdir()})

            summary = json.loads(
                (output_dir / "measurement_cli_responsibility_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(summary["line_count"], len(script.splitlines()))
            self.assertGreaterEqual(summary["import_count"], 14)
            self.assertTrue(summary["cli_entrypoint_present"])
            self.assertTrue(summary["main_function_present"])
            self.assertEqual(summary["todo_fixme_count"], 1)
            delegated_layers = {
                row["layer"]
                for row in summary["delegated_modules"]
                if row["status"] == "present"
            }
            self.assertIn("args/config/safety", delegated_layers)
            self.assertIn("output paths", delegated_layers)
            self.assertIn("report writers", delegated_layers)
            self.assertIn("review exports", delegated_layers)
            self.assertIn("audit orchestration", delegated_layers)
            self.assertIn("review workbook", delegated_layers)
            self.assertIn("Google sync", delegated_layers)

            responsibility_status = {
                row["category"]: row["status"]
                for row in summary["remaining_responsibilities"]
            }
            self.assertEqual(
                responsibility_status["PDF discovery / input selection"],
                "present",
            )
            self.assertEqual(responsibility_status["private measurement call"], "present")
            self.assertEqual(
                responsibility_status["template registry loading"],
                "present",
            )
            self.assertIn(
                "remaining direct review/export call",
                summary["remaining_direct_call_categories"],
            )
            self.assertFalse(sentinel.exists(), "fixture script must not be imported/executed")

    def test_ignores_private_and_local_output_dirs(self):
        temp, repo, _sentinel, _script = self._make_repo()
        with temp:
            output_dir, _stdout = self._run_audit(repo)
            for path in output_dir.iterdir():
                self.assertNotIn(
                    "SENTINEL_PRIVATE_VALUE",
                    path.read_text(encoding="utf-8"),
                    msg=f"private value leaked into {path}",
                )

    def test_output_records_no_pdf_ocr_google_or_model_execution(self):
        temp, repo, _sentinel, _script = self._make_repo()
        with temp:
            output_dir, _stdout = self._run_audit(repo)
            summary = json.loads(
                (output_dir / "measurement_cli_responsibility_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            safety = summary["safety"]
            self.assertFalse(safety["project_modules_imported"])
            self.assertFalse(safety["measurement_executed"])
            self.assertFalse(safety["pdf_processing_attempted"])
            self.assertFalse(safety["ocr_attempted"])
            self.assertFalse(safety["google_called"])
            self.assertFalse(safety["model_or_cloud_called"])


if __name__ == "__main__":
    unittest.main()
