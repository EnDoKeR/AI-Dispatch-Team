import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from scripts.run_ratecon_model_assisted_benchmark import (
    ModelAssistedBenchmarkError,
    main,
    run_model_assisted_benchmark,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_model_assisted"
HYBRID_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_hybrid"
GOLD_DIR = HYBRID_FIXTURES / "gold_labels_sanitized"
AUDIT = HYBRID_FIXTURES / "audit_sanitized" / "ratecon_shadow_document_pipeline_audit.jsonl"
OUTPUT_ROOT = REPO_ROOT / ".local_outputs" / "test_ratecon_model_assisted_benchmark"


class RateConModelAssistedBenchmarkTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)

    def _submission_dir(self, *fixture_names: str) -> Path:
        path = OUTPUT_ROOT / "submissions"
        path.mkdir(parents=True, exist_ok=True)
        for name in fixture_names:
            shutil.copyfile(MODEL_FIXTURES / name, path / name)
        return path

    def _baseline(self) -> Path:
        path = OUTPUT_ROOT / "manual_baseline.json"
        payload = {
            "schema_version": "ratecon_hybrid_manual_closeout_summary_v1",
            "completed_document_count": 1,
            "load_number": {"correct": 1, "wrong": 0, "missing": 0, "not_applicable_non_rc": 0},
            "total_carrier_rate": {"correct": 1, "wrong": 0, "missing": 0, "not_applicable_non_rc": 0},
            "pickup_stops": {
                "exact_complete": 1,
                "matches_uncertain_gold_review_required": 0,
                "unsafe_wrong": 0,
                "missing_review_required": 0,
                "not_applicable": 0,
            },
            "delivery_stops": {
                "exact_complete": 1,
                "matches_uncertain_gold_review_required": 0,
                "unsafe_wrong": 0,
                "missing_review_required": 0,
                "not_applicable": 0,
            },
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_benchmark_wrapper_refuses_without_confirm_flag(self):
        submissions = self._submission_dir("valid_stub_submission.model_assisted_submission.json")
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(
                    [
                        "--model-submissions-dir",
                        str(submissions),
                        "--gold-dir",
                        str(GOLD_DIR),
                        "--output-dir",
                        str(OUTPUT_ROOT / "benchmark"),
                    ]
                )
        self.assertNotEqual(context.exception.code, 0)

    def test_benchmark_wrapper_refuses_output_outside_local_outputs(self):
        submissions = self._submission_dir("valid_stub_submission.model_assisted_submission.json")
        with self.assertRaises(ModelAssistedBenchmarkError):
            run_model_assisted_benchmark(
                model_submissions_dir=submissions,
                gold_dir=GOLD_DIR,
                audit=AUDIT,
                manual_baseline_summary=self._baseline(),
                output_dir=REPO_ROOT / "model_assisted_benchmark",
            )

    def test_benchmark_wrapper_writes_summary_report_and_csvs(self):
        submissions = self._submission_dir("valid_stub_submission.model_assisted_submission.json")

        summary = run_model_assisted_benchmark(
            model_submissions_dir=submissions,
            gold_dir=GOLD_DIR,
            audit=AUDIT,
            manual_baseline_summary=self._baseline(),
            output_dir=OUTPUT_ROOT / "benchmark",
            write_review_packets=True,
        )

        self.assertEqual(summary["submission_count"], 1)
        self.assertEqual(summary["valid_submission_count"], 1)
        self.assertEqual(summary["invalid_submission_count"], 0)
        self.assertEqual(summary["model_status"], "model_output_below_manual_baseline")
        self.assertTrue((OUTPUT_ROOT / "benchmark" / "model_assisted_benchmark_summary.json").exists())
        self.assertTrue((OUTPUT_ROOT / "benchmark" / "model_assisted_benchmark_report.md").exists())
        self.assertTrue((OUTPUT_ROOT / "benchmark" / "model_assisted_field_metrics.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "benchmark" / "model_assisted_document_metrics.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "benchmark" / "model_assisted_baseline_comparison.csv").exists())

    def test_invalid_submission_is_schema_failed_and_safety_visible(self):
        submissions = self._submission_dir("invalid_external_call.model_assisted_submission.json")

        summary = run_model_assisted_benchmark(
            model_submissions_dir=submissions,
            gold_dir=GOLD_DIR,
            audit=AUDIT,
            manual_baseline_summary=self._baseline(),
            output_dir=OUTPUT_ROOT / "benchmark",
        )

        self.assertEqual(summary["valid_submission_count"], 0)
        self.assertEqual(summary["invalid_submission_count"], 1)
        self.assertEqual(summary["model_status"], "model_output_schema_failed")
        safety = (OUTPUT_ROOT / "benchmark" / "model_assisted_safety_violations.csv").read_text(encoding="utf-8")
        self.assertIn("external_call_made", safety)

    def test_no_external_calls_pdf_or_ocr(self):
        submissions = self._submission_dir("valid_stub_submission.model_assisted_submission.json")

        summary = run_model_assisted_benchmark(
            model_submissions_dir=submissions,
            gold_dir=GOLD_DIR,
            audit=AUDIT,
            manual_baseline_summary=self._baseline(),
            output_dir=OUTPUT_ROOT / "benchmark",
        )

        self.assertFalse(summary["external_api_calls_attempted"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["ai_model_invocation_attempted"])

    def test_no_private_values_in_default_output(self):
        submissions = self._submission_dir("valid_stub_submission.model_assisted_submission.json")
        payload = json.loads((submissions / "valid_stub_submission.model_assisted_submission.json").read_text(encoding="utf-8"))
        payload["result"]["file_name"] = "SECRET_PRIVATE_FILE.pdf"
        (submissions / "valid_stub_submission.model_assisted_submission.json").write_text(json.dumps(payload), encoding="utf-8")

        run_model_assisted_benchmark(
            model_submissions_dir=submissions,
            gold_dir=GOLD_DIR,
            audit=AUDIT,
            manual_baseline_summary=self._baseline(),
            output_dir=OUTPUT_ROOT / "benchmark",
        )

        output_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (OUTPUT_ROOT / "benchmark").glob("*")
            if path.is_file()
        )
        self.assertNotIn("SECRET_PRIVATE_FILE", output_text)


if __name__ == "__main__":
    unittest.main()
