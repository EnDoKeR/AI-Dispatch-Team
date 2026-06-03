import csv
import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from scripts.summarize_ratecon_hybrid_manual_pilot import (
    ManualPilotSummaryError,
    classify_pilot_outcome,
    main,
    summarize_manual_pilot,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "ratecon_hybrid"


class RateConHybridManualPilotSummaryTests(unittest.TestCase):
    def setUp(self):
        self.root = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_manual_pilot_summary"
        shutil.rmtree(self.root, ignore_errors=True)
        self.benchmark_dir = self.root / "benchmark"
        self.output_dir = self.root / "summary"
        self.benchmark_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _summary_payload(
        self,
        *,
        schema_errors=0,
        auto_accept=0,
        missing_evidence=0,
        unsafe_wrong=0,
        load_wrong=0,
        rate_wrong=0,
        uncertain_gold=0,
        secret_marker=None,
    ):
        payload = {
            "schema_version": "ratecon_hybrid_benchmark_summary_v1",
            "hybrid_result_count": 5,
            "schema_error_count": schema_errors,
            "one_screen_summary": {
                "results": 5,
                "schema_errors": schema_errors,
                "error_cases": schema_errors + auto_accept + missing_evidence + unsafe_wrong + load_wrong + rate_wrong,
                "missing_evidence": missing_evidence,
                "stop_auto_accept_violations": auto_accept,
                "unsafe_wrong_stops": unsafe_wrong,
                "gold_uncertain_review_required": uncertain_gold,
            },
            "field_metrics": {
                "load_number": {"correct": 5 - load_wrong, "wrong": load_wrong, "missing": 0},
                "total_carrier_rate": {"correct": 5 - rate_wrong, "wrong": rate_wrong, "missing": 0},
            },
            "stop_metrics": {
                "pickup_stops": {"exact_complete": 5, "unsafe_wrong": 0, "missing_review_required": 0},
                "delivery_stops": {
                    "exact_complete": 5 - uncertain_gold - unsafe_wrong,
                    "unsafe_wrong": unsafe_wrong,
                    "matches_uncertain_gold_review_required": uncertain_gold,
                    "missing_review_required": 0,
                },
            },
            "gold_uncertain_metrics": {"review_required": uncertain_gold, "matches_uncertain_gold": uncertain_gold},
            "safety": {
                "external_api_calls_attempted": False,
                "pdf_processing_attempted": False,
                "ai_model_invocation_attempted": False,
            },
        }
        if secret_marker:
            payload["private_debug_value"] = secret_marker
        return payload

    def _write_benchmark(self, payload=None):
        payload = payload or self._summary_payload()
        (self.benchmark_dir / "hybrid_benchmark_summary.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        with (self.benchmark_dir / "hybrid_document_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["document_id", "file_name_or_label", "document_type"])
            writer.writeheader()
            writer.writerow(
                {
                    "document_id": "DOC_FIXTURE_PERFECT",
                    "file_name_or_label": "fixture_perfect_rate_confirmation.pdf",
                    "document_type": "rate_confirmation",
                }
            )

    def _read_csv(self, path):
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_refuses_without_confirm_flag(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(["--benchmark-dir", str(self.benchmark_dir)])

        self.assertNotEqual(context.exception.code, 0)

    def test_refuses_output_outside_local_outputs(self):
        self._write_benchmark()

        with self.assertRaises(ManualPilotSummaryError):
            summarize_manual_pilot(
                benchmark_dir=self.benchmark_dir,
                output_dir=REPO_ROOT / "tmp_manual_pilot_summary",
            )

    def test_pilot_with_schema_errors_failed_schema(self):
        payload = self._summary_payload(schema_errors=1)

        self.assertEqual(classify_pilot_outcome(payload), "pilot_failed_schema")

    def test_pilot_with_auto_accept_failed_safety(self):
        payload = self._summary_payload(auto_accept=1)

        self.assertEqual(classify_pilot_outcome(payload), "pilot_failed_safety")

    def test_pilot_with_missing_evidence_failed_safety(self):
        payload = self._summary_payload(missing_evidence=1)

        self.assertEqual(classify_pilot_outcome(payload), "pilot_failed_safety")

    def test_pilot_with_unsafe_wrong_failed_accuracy(self):
        payload = self._summary_payload(unsafe_wrong=1)

        self.assertEqual(classify_pilot_outcome(payload), "pilot_failed_accuracy")

    def test_pilot_with_only_uncertain_gold_passed_with_review_items(self):
        self._write_benchmark(self._summary_payload(uncertain_gold=1))

        summary = summarize_manual_pilot(benchmark_dir=self.benchmark_dir, output_dir=self.output_dir)

        self.assertEqual(summary["pilot_status"], "pilot_passed_with_review_items")
        self.assertEqual(summary["gold_uncertain_review_required_count"], 1)
        self.assertTrue((self.output_dir / "manual_pilot_summary.md").exists())
        criteria = self._read_csv(self.output_dir / "manual_pilot_success_criteria.csv")
        uncertain_rows = [row for row in criteria if row["criterion"] == "uncertain_gold_review_required"]
        self.assertEqual(uncertain_rows[0]["passes"], "true")

    def test_clean_pilot_passed(self):
        self._write_benchmark(self._summary_payload())

        summary = summarize_manual_pilot(benchmark_dir=self.benchmark_dir, output_dir=self.output_dir)

        self.assertEqual(summary["pilot_status"], "pilot_passed")
        self.assertEqual(summary["unsafe_wrong_stop_count"], 0)

    def test_next_action_csv_is_written(self):
        self._write_benchmark(self._summary_payload(uncertain_gold=1))

        summary = summarize_manual_pilot(benchmark_dir=self.benchmark_dir, output_dir=self.output_dir)

        self.assertGreater(summary["next_action_count"], 0)
        rows = self._read_csv(self.output_dir / "manual_pilot_next_actions.csv")
        actions = {row["recommended_action"] for row in rows}
        self.assertIn("expand_manual_pilot_to_next_5_to_10_documents", actions)
        self.assertIn("keep_auto_accept_false", actions)

    def test_next_batch_plan_generated_from_sanitized_audit_and_gold(self):
        self._write_benchmark(self._summary_payload(uncertain_gold=1))

        summary = summarize_manual_pilot(
            benchmark_dir=self.benchmark_dir,
            output_dir=self.output_dir,
            write_next_batch_plan=True,
            audit=FIXTURE_ROOT / "audit_sanitized" / "ratecon_shadow_document_pipeline_audit.jsonl",
            gold_dir=FIXTURE_ROOT / "gold_labels_sanitized",
        )

        self.assertGreater(summary["next_batch_plan_count"], 0)
        plan_rows = self._read_csv(self.output_dir / "manual_pilot_next_batch_plan.csv")
        self.assertGreater(len(plan_rows), 0)
        self.assertIn("document_id", plan_rows[0])
        self.assertIn("suggested_pattern", plan_rows[0])
        self.assertNotIn("DOC_FIXTURE_PERFECT", {row["document_id"] for row in plan_rows})

    def test_no_private_values_in_default_output(self):
        self._write_benchmark(self._summary_payload(secret_marker="SECRET_PRIVATE_VALUE"))

        summarize_manual_pilot(benchmark_dir=self.benchmark_dir, output_dir=self.output_dir)

        output_text = (self.output_dir / "manual_pilot_summary.md").read_text(encoding="utf-8")
        output_text += (self.output_dir / "manual_pilot_summary.json").read_text(encoding="utf-8")
        self.assertNotIn("SECRET_PRIVATE_VALUE", output_text)

    def test_no_external_calls_or_pdf_processing(self):
        self._write_benchmark(self._summary_payload())

        summary = summarize_manual_pilot(benchmark_dir=self.benchmark_dir, output_dir=self.output_dir)

        self.assertFalse(summary["external_api_calls_attempted"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ai_model_invocation_attempted"])


if __name__ == "__main__":
    unittest.main()
