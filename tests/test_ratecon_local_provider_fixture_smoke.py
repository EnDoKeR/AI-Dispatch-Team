import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from app.document_ai.ratecon_local_provider_readiness import RateConLocalProviderReadinessError
from scripts.run_ratecon_local_provider_fixture_smoke_test import main, run_fixture_smoke_test


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / ".local_outputs" / "test_ratecon_local_provider_fixture_smoke"


class RateConLocalProviderFixtureSmokeTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)

    def test_smoke_test_refuses_without_confirm_flag(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(["--output-dir", str(OUTPUT_ROOT / "smoke")])
        self.assertNotEqual(context.exception.code, 0)

    def test_smoke_test_refuses_output_outside_local_outputs(self):
        with self.assertRaises(RateConLocalProviderReadinessError):
            run_fixture_smoke_test(output_dir=REPO_ROOT / "fixture_smoke")

    def test_smoke_test_runs_with_sanitized_fixtures_only(self):
        summary = run_fixture_smoke_test(output_dir=OUTPUT_ROOT / "smoke")

        self.assertEqual(summary["status"], "fixture_smoke_passed_no_model_execution")
        self.assertTrue(summary["provider_config_valid"])
        self.assertFalse(summary["external_api_calls_attempted"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["ai_model_invocation_attempted"])
        self.assertFalse(summary["model_execution_attempted"])
        self.assertFalse(summary["external_call_attempted"])
        self.assertFalse(summary["private_data_used"])
        self.assertIn("provider_config_status", summary)
        self.assertIn("benchmark_status", summary)
        self.assertIn("safety_violation_count", summary)
        self.assertTrue((OUTPUT_ROOT / "smoke" / "fixture_smoke_summary.json").exists())
        self.assertTrue((OUTPUT_ROOT / "smoke" / "fixture_smoke_report.md").exists())
        self.assertTrue((OUTPUT_ROOT / "smoke" / "fixture_smoke_gate_results.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "smoke" / "fixture_smoke_artifacts_index.csv").exists())

    def test_smoke_test_output_says_no_model_execution(self):
        run_fixture_smoke_test(output_dir=OUTPUT_ROOT / "smoke")

        report = (OUTPUT_ROOT / "smoke" / "fixture_smoke_report.md").read_text(encoding="utf-8")
        self.assertIn("no model call", report)
        self.assertIn("processed no PDFs", report)
        self.assertIn("ran no OCR", report)

    def test_no_private_values_in_default_smoke_output(self):
        run_fixture_smoke_test(output_dir=OUTPUT_ROOT / "smoke")

        output_text = "\n".join(path.read_text(encoding="utf-8") for path in (OUTPUT_ROOT / "smoke").glob("*") if path.is_file())
        output_text += "\n".join(path.read_text(encoding="utf-8") for path in (OUTPUT_ROOT / "smoke" / "readiness_dry_run").glob("*") if path.is_file())
        self.assertNotIn("SECRET_PRIVATE", output_text)


if __name__ == "__main__":
    unittest.main()
