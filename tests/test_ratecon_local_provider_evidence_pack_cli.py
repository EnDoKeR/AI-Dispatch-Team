import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from scripts.create_ratecon_local_provider_evidence_pack import (
    RateConLocalProviderEvidencePackError,
    create_evidence_pack_outputs,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
READINESS_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_local_provider_readiness"
PROVIDER_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_model_provider"
EVIDENCE_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_local_provider_evidence_pack"
OUTPUT_ROOT = REPO_ROOT / ".local_outputs" / "test_ratecon_local_provider_evidence_pack_cli"


class RateConLocalProviderEvidencePackCliTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        self.smoke_dir = OUTPUT_ROOT / "smoke"
        self.readiness_report_dir = OUTPUT_ROOT / "readiness_report"
        self.smoke_dir.mkdir(parents=True, exist_ok=True)
        self.readiness_report_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            EVIDENCE_FIXTURES / "valid_evidence_inputs" / "fixture_smoke_summary.json",
            self.smoke_dir / "fixture_smoke_summary.json",
        )
        shutil.copyfile(
            EVIDENCE_FIXTURES / "valid_evidence_inputs" / "readiness_summary.json",
            self.readiness_report_dir / "readiness_summary.json",
        )

    def tearDown(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)

    def test_cli_refuses_without_confirm_flag(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(
                    [
                        "--readiness-file",
                        str(READINESS_FIXTURES / "valid_fixture_only_readiness.json"),
                        "--provider-config",
                        str(PROVIDER_FIXTURES / "valid_stub_provider_config.json"),
                        "--smoke-dir",
                        str(self.smoke_dir),
                        "--readiness-report-dir",
                        str(self.readiness_report_dir),
                        "--output-dir",
                        str(OUTPUT_ROOT / "pack"),
                    ]
                )
        self.assertNotEqual(context.exception.code, 0)

    def test_cli_refuses_output_outside_local_outputs(self):
        with self.assertRaises(RateConLocalProviderEvidencePackError):
            create_evidence_pack_outputs(
                readiness_file=READINESS_FIXTURES / "valid_fixture_only_readiness.json",
                provider_config=PROVIDER_FIXTURES / "valid_stub_provider_config.json",
                smoke_dir=self.smoke_dir,
                readiness_report_dir=self.readiness_report_dir,
                output_dir=REPO_ROOT / "evidence_pack",
            )

    def test_cli_writes_summary_report_and_csv_files(self):
        code = main(
            [
                "--readiness-file",
                str(READINESS_FIXTURES / "valid_fixture_only_readiness.json"),
                "--provider-config",
                str(PROVIDER_FIXTURES / "valid_stub_provider_config.json"),
                "--smoke-dir",
                str(self.smoke_dir),
                "--readiness-report-dir",
                str(self.readiness_report_dir),
                "--output-dir",
                str(OUTPUT_ROOT / "pack"),
                "--confirm-private-local-run",
                "--include-fixture-benchmark",
            ]
        )

        self.assertEqual(code, 0)
        self.assertTrue((OUTPUT_ROOT / "pack" / "local_provider_evidence_pack_summary.json").exists())
        self.assertTrue((OUTPUT_ROOT / "pack" / "local_provider_evidence_pack_report.md").exists())
        self.assertTrue((OUTPUT_ROOT / "pack" / "local_provider_evidence_gate_results.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "pack" / "local_provider_evidence_blockers.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "pack" / "local_provider_evidence_next_actions.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "pack" / "local_provider_evidence_artifact_index.csv").exists())
        summary = json.loads((OUTPUT_ROOT / "pack" / "local_provider_evidence_pack_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["recommendation"], "ready_for_separate_local_provider_design_pr")

    def test_missing_smoke_outputs_do_not_crash_and_continue_fixture_only(self):
        pack = create_evidence_pack_outputs(
            readiness_file=READINESS_FIXTURES / "valid_fixture_only_readiness.json",
            provider_config=PROVIDER_FIXTURES / "valid_stub_provider_config.json",
            smoke_dir=OUTPUT_ROOT / "missing_smoke",
            readiness_report_dir=self.readiness_report_dir,
            output_dir=OUTPUT_ROOT / "pack",
        )

        self.assertEqual(pack["recommendation"], "fixture_only_continue")

    def test_invalid_provider_config_rejects(self):
        pack = create_evidence_pack_outputs(
            readiness_file=READINESS_FIXTURES / "valid_fixture_only_readiness.json",
            provider_config=PROVIDER_FIXTURES / "invalid_external_calls_config.json",
            smoke_dir=self.smoke_dir,
            readiness_report_dir=self.readiness_report_dir,
            output_dir=OUTPUT_ROOT / "pack",
        )

        self.assertEqual(pack["recommendation"], "reject")

    def test_no_private_values_in_default_output(self):
        create_evidence_pack_outputs(
            readiness_file=READINESS_FIXTURES / "valid_fixture_only_readiness.json",
            provider_config=PROVIDER_FIXTURES / "valid_stub_provider_config.json",
            smoke_dir=self.smoke_dir,
            readiness_report_dir=self.readiness_report_dir,
            output_dir=OUTPUT_ROOT / "pack",
        )
        output_text = "\n".join(path.read_text(encoding="utf-8") for path in (OUTPUT_ROOT / "pack").glob("*") if path.is_file())
        self.assertNotIn("SECRET_PRIVATE", output_text)


if __name__ == "__main__":
    unittest.main()
