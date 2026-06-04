import io
import json
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.ratecon_local_provider_readiness_cli import (
    RateConLocalProviderReadinessError,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
READINESS_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_local_provider_readiness"
PROVIDER_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_model_provider"
OUTPUT_ROOT = REPO_ROOT / ".local_outputs" / "test_ratecon_local_provider_readiness_cli"


class RateConLocalProviderReadinessCliTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)

    def test_create_template_refuses_without_confirm_flag(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(["create-template", "--output", str(OUTPUT_ROOT / "template.json")])
        self.assertNotEqual(context.exception.code, 0)

    def test_create_template_writes_to_local_outputs(self):
        code = main(
            [
                "create-template",
                "--output",
                str(OUTPUT_ROOT / "template.json"),
                "--confirm-private-local-run",
            ]
        )

        self.assertEqual(code, 0)
        payload = json.loads((OUTPUT_ROOT / "template.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "ratecon_local_provider_readiness_v1")
        self.assertFalse(payload["approval"]["approved_for_private_local_only"])

    def test_cli_refuses_output_outside_local_outputs(self):
        with self.assertRaises(RateConLocalProviderReadinessError):
            main(
                [
                    "create-template",
                    "--output",
                    str(REPO_ROOT / "readiness_template.json"),
                    "--confirm-private-local-run",
                ]
            )

    def test_validate_works_on_fixture_file(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(
                [
                    "validate",
                    "--readiness-file",
                    str(READINESS_FIXTURES / "valid_fixture_only_readiness.json"),
                    "--confirm-private-local-run",
                ]
            )

        self.assertEqual(code, 0)
        self.assertIn("fixture_only_plan_valid", stdout.getvalue())

    def test_dry_run_report_writes_report_json_and_csv_files(self):
        code = main(
            [
                "dry-run-report",
                "--readiness-file",
                str(READINESS_FIXTURES / "valid_fixture_only_readiness.json"),
                "--provider-config",
                str(PROVIDER_FIXTURES / "valid_stub_provider_config.json"),
                "--output-dir",
                str(OUTPUT_ROOT / "dry_run"),
                "--confirm-private-local-run",
            ]
        )

        self.assertEqual(code, 0)
        self.assertTrue((OUTPUT_ROOT / "dry_run" / "readiness_report.md").exists())
        self.assertTrue((OUTPUT_ROOT / "dry_run" / "readiness_summary.json").exists())
        self.assertTrue((OUTPUT_ROOT / "dry_run" / "readiness_gate_results.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "dry_run" / "readiness_next_actions.csv").exists())
        summary = json.loads((OUTPUT_ROOT / "dry_run" / "readiness_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["provider_readiness_status"], "fixture_only_plan_valid")
        self.assertTrue(summary["provider_execution_allowed"])

    def test_no_private_values_in_default_output(self):
        main(
            [
                "dry-run-report",
                "--readiness-file",
                str(READINESS_FIXTURES / "valid_fixture_only_readiness.json"),
                "--provider-config",
                str(PROVIDER_FIXTURES / "valid_stub_provider_config.json"),
                "--output-dir",
                str(OUTPUT_ROOT / "dry_run"),
                "--confirm-private-local-run",
            ]
        )
        output_text = "\n".join(path.read_text(encoding="utf-8") for path in (OUTPUT_ROOT / "dry_run").glob("*") if path.is_file())
        self.assertNotIn("SECRET_PRIVATE", output_text)


if __name__ == "__main__":
    unittest.main()
