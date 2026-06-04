import io
import json
import shutil
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from scripts.create_ratecon_model_assisted_stub_outputs import (
    ModelAssistedStubOutputError,
    create_model_assisted_stub_outputs,
)
from scripts.ratecon_model_provider_cli import RateConModelProviderError, main


REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_model_provider"
MODEL_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_model_assisted"
OUTPUT_ROOT = REPO_ROOT / ".local_outputs" / "test_ratecon_model_provider_cli"


class RateConModelProviderCliTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)

    def test_list_providers_outputs_required_providers(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["list-providers"])

        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        names = {provider["provider_name"] for provider in payload["providers"]}
        self.assertIn("stub_empty_v1", names)
        self.assertIn("manual_baseline_reference_v1", names)
        self.assertIn("local_model_placeholder_v1", names)
        self.assertIn("cloud_model_placeholder_v1", names)

    def test_validate_config_refuses_without_confirm_flag(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(["validate-config", "--config", str(PROVIDER_FIXTURES / "valid_stub_provider_config.json")])
        self.assertNotEqual(context.exception.code, 0)

    def test_validate_config_accepts_valid_stub(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(
                [
                    "validate-config",
                    "--config",
                    str(PROVIDER_FIXTURES / "valid_stub_provider_config.json"),
                    "--confirm-private-local-run",
                ]
            )

        self.assertEqual(code, 0)
        self.assertIn("valid: True", stdout.getvalue())

    def test_validate_config_rejects_unsafe_configs(self):
        for fixture_name in (
            "invalid_external_calls_config.json",
            "invalid_pdf_processing_config.json",
            "invalid_cloud_provider_config.json",
            "invalid_secret_key_config.json",
        ):
            with self.subTest(fixture_name=fixture_name):
                code = main(
                    [
                        "validate-config",
                        "--config",
                        str(PROVIDER_FIXTURES / fixture_name),
                        "--confirm-private-local-run",
                    ]
                )
                self.assertEqual(code, 2)

    def test_dry_run_refuses_without_confirm_flag(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(
                    [
                        "dry-run",
                        "--config",
                        str(PROVIDER_FIXTURES / "valid_stub_provider_config.json"),
                        "--templates-dir",
                        str(MODEL_FIXTURES),
                        "--output-dir",
                        str(OUTPUT_ROOT / "dry_run"),
                    ]
                )
        self.assertNotEqual(context.exception.code, 0)

    def test_dry_run_refuses_output_outside_local_outputs(self):
        with self.assertRaises(RateConModelProviderError):
            main(
                [
                    "dry-run",
                    "--config",
                    str(PROVIDER_FIXTURES / "valid_stub_provider_config.json"),
                    "--templates-dir",
                    str(MODEL_FIXTURES),
                    "--output-dir",
                    str(REPO_ROOT / "provider_dry_run"),
                    "--confirm-private-local-run",
                ]
            )

    def test_dry_run_writes_plan_report_and_gates(self):
        code = main(
            [
                "dry-run",
                "--config",
                str(PROVIDER_FIXTURES / "valid_stub_provider_config.json"),
                "--templates-dir",
                str(MODEL_FIXTURES),
                "--output-dir",
                str(OUTPUT_ROOT / "dry_run"),
                "--confirm-private-local-run",
            ]
        )

        self.assertEqual(code, 0)
        self.assertTrue((OUTPUT_ROOT / "dry_run" / "provider_dry_run_plan.json").exists())
        self.assertTrue((OUTPUT_ROOT / "dry_run" / "provider_dry_run_report.md").exists())
        self.assertTrue((OUTPUT_ROOT / "dry_run" / "provider_safety_gates.csv").exists())
        plan = json.loads((OUTPUT_ROOT / "dry_run" / "provider_dry_run_plan.json").read_text(encoding="utf-8"))
        self.assertFalse(plan["external_api_calls_attempted"])
        self.assertFalse(plan["pdf_processing_attempted"])
        self.assertFalse(plan["ocr_attempted"])
        self.assertFalse(plan["ai_model_invocation_attempted"])

    def test_stub_output_generator_accepts_valid_provider_config(self):
        summary = create_model_assisted_stub_outputs(
            templates_dir=MODEL_FIXTURES,
            output_dir=OUTPUT_ROOT / "stub_outputs",
            fixture_mode=False,
            provider_config=PROVIDER_FIXTURES / "valid_stub_provider_config.json",
            max_docs=1,
        )

        self.assertEqual(summary["submission_count"], 1)
        self.assertEqual(summary["provider_name"], "stub_empty_v1")
        payload = json.loads(next((OUTPUT_ROOT / "stub_outputs").glob("*.model_assisted_submission.json")).read_text(encoding="utf-8"))
        self.assertEqual(payload["provider"]["provider_name"], "stub_empty_v1")
        self.assertEqual(payload["provider_registry"]["provider_status"], "ready_stub_only")

    def test_stub_output_generator_rejects_unsafe_provider_config(self):
        with self.assertRaises(ModelAssistedStubOutputError):
            create_model_assisted_stub_outputs(
                templates_dir=MODEL_FIXTURES,
                output_dir=OUTPUT_ROOT / "stub_outputs",
                fixture_mode=False,
                provider_config=PROVIDER_FIXTURES / "invalid_external_calls_config.json",
                max_docs=1,
            )

    def test_no_private_values_in_default_output(self):
        main(
            [
                "dry-run",
                "--config",
                str(PROVIDER_FIXTURES / "valid_stub_provider_config.json"),
                "--templates-dir",
                str(MODEL_FIXTURES),
                "--output-dir",
                str(OUTPUT_ROOT / "dry_run"),
                "--confirm-private-local-run",
            ]
        )
        output_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (OUTPUT_ROOT / "dry_run").glob("*")
            if path.is_file()
        )
        self.assertNotIn("SECRET_PRIVATE", output_text)


if __name__ == "__main__":
    unittest.main()
