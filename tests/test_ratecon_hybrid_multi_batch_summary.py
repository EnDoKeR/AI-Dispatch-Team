import csv
import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from scripts.create_ratecon_hybrid_next_batch_packet import create_next_batch_packet
from scripts.run_ratecon_hybrid_benchmark import run_hybrid_benchmark
from scripts.summarize_ratecon_hybrid_batches import (
    HybridMultiBatchSummaryError,
    classify_multi_batch_status,
    main,
    summarize_hybrid_batches,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "ratecon_hybrid"
AUDIT = FIXTURE_ROOT / "audit_sanitized" / "ratecon_shadow_document_pipeline_audit.jsonl"
GOLD_DIR = FIXTURE_ROOT / "gold_labels_sanitized"
OUTPUT_ROOT = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_multi_batch_summary"


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class RateConHybridMultiBatchSummaryTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)

    def _benchmark_dir(
        self,
        name: str,
        docs: list[dict[str, object]],
        *,
        schema_errors: int = 0,
        auto_accept: int = 0,
        missing_evidence: int = 0,
        unsafe_wrong: int = 0,
    ) -> Path:
        path = OUTPUT_ROOT / name
        path.mkdir(parents=True, exist_ok=True)
        summary = {
            "schema_version": "ratecon_hybrid_benchmark_summary_v1",
            "hybrid_result_count": len(docs),
            "schema_error_count": schema_errors,
            "one_screen_summary": {
                "results": len(docs),
                "schema_errors": schema_errors,
                "unfilled_manual_templates": 0,
                "error_cases": schema_errors + auto_accept + missing_evidence + unsafe_wrong,
                "missing_evidence": missing_evidence,
                "stop_auto_accept_violations": auto_accept,
                "unsafe_wrong_stops": unsafe_wrong,
                "gold_uncertain_review_required": sum(
                    1
                    for doc in docs
                    for key in ("pickup_tier", "delivery_tier")
                    if str(doc.get(key, "")).endswith("_uncertain_gold_review_required")
                ),
            },
            "field_metrics": {},
            "stop_metrics": {},
            "review_policy": {"stop_auto_accept_violation": auto_accept},
            "evidence_metrics": {"missing_evidence": missing_evidence},
            "safety": {
                "external_api_calls_attempted": False,
                "pdf_processing_attempted": False,
                "ai_model_invocation_attempted": False,
            },
        }
        (path / "hybrid_benchmark_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        _write_csv(
            path / "hybrid_document_metrics.csv",
            [
                {
                    "document_id": doc["document_id"],
                    "file_name_or_label": doc.get("file_name_or_label", f"{doc['document_id']}.pdf"),
                    "document_type": doc.get("document_type", "rate_confirmation"),
                    "schema_valid": "true",
                    "document_type_status": "correct",
                    "gold_matched": "true",
                    "requires_human_review": "true",
                    "private_local_only": "true",
                }
                for doc in docs
            ],
            [
                "document_id",
                "file_name_or_label",
                "document_type",
                "schema_valid",
                "document_type_status",
                "gold_matched",
                "requires_human_review",
                "private_local_only",
            ],
        )
        field_rows: list[dict[str, object]] = []
        review_rows: list[dict[str, object]] = []
        for doc in docs:
            document_id = str(doc["document_id"])
            for field_name in ("load_number", "total_carrier_rate"):
                field_rows.append(
                    {
                        "document_id": document_id,
                        "field": field_name,
                        "stop_index": "",
                        "status": doc.get(f"{field_name}_status", "exact"),
                        "tier": "",
                        "issues": "",
                        "confidence": 0.99,
                        "confidence_bucket": "gte_0_90",
                        "has_evidence": "true",
                        "requires_human_review": "true",
                        "auto_accept": "false",
                        "gold_uncertain_status": "",
                    }
                )
            for field_name, tier_key, role in (
                ("pickup_stops", "pickup_tier", "pickup"),
                ("delivery_stops", "delivery_tier", "delivery"),
            ):
                tier = str(doc.get(tier_key, "exact_complete"))
                field_rows.append(
                    {
                        "document_id": document_id,
                        "field": field_name,
                        "stop_index": "1",
                        "status": "gold_uncertain" if "uncertain" in tier else "exact",
                        "tier": tier,
                        "issues": "gold_uncertain_review_required" if "uncertain" in tier else "",
                        "confidence": 0.98,
                        "confidence_bucket": "gte_0_90",
                        "has_evidence": "true",
                        "requires_human_review": "true",
                        "auto_accept": "false",
                        "gold_uncertain_status": tier if "uncertain" in tier else "",
                    }
                )
                review_rows.append(
                    {
                        "document_id": document_id,
                        "file_name_or_label": doc.get("file_name_or_label", f"{document_id}.pdf"),
                        "document_type": doc.get("document_type", "rate_confirmation"),
                        "field": field_name,
                        "stop_role": role,
                        "stop_index": "1",
                        "status": tier,
                        "review_reason": "gold_uncertain_review_required" if "uncertain" in tier else "",
                        "evidence_status": "present",
                        "confidence": 0.98,
                        "auto_accept_violation": "false",
                        "missing_evidence": "false",
                        "recommended_action": "needs_human_review" if "uncertain" in tier else "accept_for_review_draft",
                    }
                )
        _write_csv(
            path / "hybrid_field_metrics.csv",
            field_rows,
            [
                "document_id",
                "field",
                "stop_index",
                "status",
                "tier",
                "issues",
                "confidence",
                "confidence_bucket",
                "has_evidence",
                "requires_human_review",
                "auto_accept",
                "gold_uncertain_status",
            ],
        )
        _write_csv(
            path / "hybrid_review_items.csv",
            review_rows,
            [
                "document_id",
                "file_name_or_label",
                "document_type",
                "field",
                "stop_role",
                "stop_index",
                "status",
                "review_reason",
                "evidence_status",
                "confidence",
                "auto_accept_violation",
                "missing_evidence",
                "recommended_action",
            ],
        )
        _write_csv(path / "hybrid_schema_errors.csv", [], ["file", "document_id", "errors"])
        return path

    def _clean_batches(self):
        batch1 = self._benchmark_dir(
            "batch1",
            [
                {"document_id": "DOC_FIXTURE_PERFECT"},
                {"document_id": "DOC_FIXTURE_PARTIAL_STOP", "delivery_tier": "matches_uncertain_gold_review_required"},
            ],
        )
        batch2 = self._benchmark_dir(
            "batch2",
            [
                {"document_id": "DOC_FIXTURE_MISSING_EVIDENCE"},
                {"document_id": "DOC_FIXTURE_UNSAFE_WRONG_STOP", "pickup_tier": "matches_uncertain_gold_review_required"},
                {"document_id": "DOC_FIXTURE_PERFECT"},
            ],
        )
        return batch1, batch2

    def test_script_refuses_without_confirm_flag(self):
        batch1, _ = self._clean_batches()
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(["--benchmark-dir", str(batch1), "--output-dir", str(OUTPUT_ROOT / "summary")])
        self.assertNotEqual(context.exception.code, 0)

    def test_refuses_output_outside_local_outputs(self):
        batch1, _ = self._clean_batches()
        with self.assertRaises(HybridMultiBatchSummaryError):
            summarize_hybrid_batches(
                benchmark_dirs=[batch1],
                output_dir=REPO_ROOT / "tmp_multi_batch_summary",
            )

    def test_aggregates_two_benchmark_dirs_and_deduplicates(self):
        batch1, batch2 = self._clean_batches()
        summary = summarize_hybrid_batches(
            benchmark_dirs=[batch1, batch2],
            output_dir=OUTPUT_ROOT / "summary",
        )
        self.assertEqual(summary["aggregate_document_count"], 4)
        self.assertEqual(summary["duplicate_document_count"], 1)
        self.assertEqual(summary["field_metrics"]["load_number"], {"correct": 4, "wrong": 0, "missing": 0, "high_confidence_wrong": 0})
        self.assertEqual(summary["field_metrics"]["total_carrier_rate"]["correct"], 4)
        self.assertEqual(summary["stop_metrics"]["pickup_stops"]["exact_complete"], 3)
        self.assertEqual(summary["stop_metrics"]["pickup_stops"]["matches_uncertain_gold_review_required"], 1)
        self.assertEqual(summary["stop_metrics"]["delivery_stops"]["exact_complete"], 3)
        self.assertEqual(summary["stop_metrics"]["delivery_stops"]["matches_uncertain_gold_review_required"], 1)
        coverage = _read_csv(OUTPUT_ROOT / "summary" / "multi_batch_document_coverage.csv")
        self.assertTrue(any(row["included_in_aggregate"] == "false" for row in coverage))

    def test_status_validated_with_review_items_for_uncertain_only(self):
        batch1, batch2 = self._clean_batches()
        summary = summarize_hybrid_batches(
            benchmark_dirs=[batch1, batch2],
            output_dir=OUTPUT_ROOT / "summary",
        )
        self.assertEqual(summary["aggregate_status"], "manual_hybrid_validated_with_review_items")
        self.assertEqual(classify_multi_batch_status(summary), "manual_hybrid_validated_with_review_items")

    def test_status_fails_if_schema_error_exists(self):
        batch = self._benchmark_dir("batch_schema", [{"document_id": "DOC_FIXTURE_PERFECT"}], schema_errors=1)
        summary = summarize_hybrid_batches(benchmark_dirs=[batch], output_dir=OUTPUT_ROOT / "summary")
        self.assertEqual(summary["aggregate_status"], "manual_hybrid_failed_schema")

    def test_status_fails_if_auto_accept_violation_exists(self):
        batch = self._benchmark_dir("batch_auto", [{"document_id": "DOC_FIXTURE_PERFECT"}], auto_accept=1)
        summary = summarize_hybrid_batches(benchmark_dirs=[batch], output_dir=OUTPUT_ROOT / "summary")
        self.assertEqual(summary["aggregate_status"], "manual_hybrid_failed_safety")

    def test_status_fails_if_missing_evidence_exists(self):
        batch = self._benchmark_dir("batch_evidence", [{"document_id": "DOC_FIXTURE_PERFECT"}], missing_evidence=1)
        summary = summarize_hybrid_batches(benchmark_dirs=[batch], output_dir=OUTPUT_ROOT / "summary")
        self.assertEqual(summary["aggregate_status"], "manual_hybrid_failed_safety")

    def test_status_fails_if_unsafe_wrong_exists(self):
        batch = self._benchmark_dir(
            "batch_unsafe",
            [{"document_id": "DOC_FIXTURE_PERFECT", "pickup_tier": "unsafe_wrong"}],
            unsafe_wrong=1,
        )
        summary = summarize_hybrid_batches(benchmark_dirs=[batch], output_dir=OUTPUT_ROOT / "summary")
        self.assertEqual(summary["aggregate_status"], "manual_hybrid_failed_accuracy")

    def test_remaining_plan_excludes_completed_docs_and_has_columns(self):
        batch1, batch2 = self._clean_batches()
        summary = summarize_hybrid_batches(
            benchmark_dirs=[batch1, batch2],
            output_dir=OUTPUT_ROOT / "summary",
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            write_remaining_plan=True,
        )
        self.assertGreater(summary["remaining_plan_count"], 0)
        rows = _read_csv(OUTPUT_ROOT / "summary" / "remaining_manual_batch_plan.csv")
        self.assertGreater(len(rows), 0)
        self.assertIn("already_completed", rows[0])
        self.assertIn("duplicate_group", rows[0])
        completed = set(summary["completed_document_ids"])
        self.assertFalse(any(row["document_id"] in completed for row in rows))

    def test_optional_third_batch_packet_can_be_generated_from_remaining_plan(self):
        batch1, batch2 = self._clean_batches()
        summarize_hybrid_batches(
            benchmark_dirs=[batch1, batch2],
            output_dir=OUTPUT_ROOT / "summary",
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            write_remaining_plan=True,
        )
        packet_summary = create_next_batch_packet(
            next_batch_plan=OUTPUT_ROOT / "summary" / "remaining_manual_batch_plan.csv",
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "third_batch_packet",
            max_docs=2,
        )
        self.assertGreater(packet_summary["template_count"], 0)
        self.assertEqual(packet_summary["packet_prefix"], "third_batch")
        self.assertTrue((OUTPUT_ROOT / "third_batch_packet" / "third_batch_summary.json").exists())
        self.assertTrue((OUTPUT_ROOT / "third_batch_packet" / "third_batch_document_index.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "third_batch_packet" / "third_batch_checklist.csv").exists())
        benchmark_summary = run_hybrid_benchmark(
            hybrid_results_dir=OUTPUT_ROOT / "third_batch_packet" / "templates",
            gold_dir=GOLD_DIR,
            audit=AUDIT,
            output_dir=OUTPUT_ROOT / "third_batch_benchmark_unfilled",
            allow_unfilled_manual_templates=True,
            write_review_packets=True,
        )
        self.assertEqual(benchmark_summary["schema_error_count"], 0)
        self.assertEqual(benchmark_summary["unfilled_manual_template_count"], packet_summary["template_count"])

    def test_no_external_calls_or_pdf_processing(self):
        batch1, batch2 = self._clean_batches()
        summary = summarize_hybrid_batches(
            benchmark_dirs=[batch1, batch2],
            output_dir=OUTPUT_ROOT / "summary",
        )
        self.assertFalse(summary["external_api_calls_attempted"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["ai_model_invocation_attempted"])
        self.assertFalse(summary["gold_labels_modified"])
        self.assertFalse(summary["filled_hybrid_templates_modified"])

    def test_no_private_values_in_default_outputs(self):
        batch = self._benchmark_dir(
            "batch_private",
            [{"document_id": "DOC_FIXTURE_PERFECT", "file_name_or_label": "SECRET_PRIVATE_FILE.pdf"}],
        )
        summarize_hybrid_batches(benchmark_dirs=[batch], output_dir=OUTPUT_ROOT / "summary")
        output_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (OUTPUT_ROOT / "summary").glob("*")
            if path.is_file()
        )
        self.assertNotIn("SECRET_PRIVATE_FILE", output_text)


if __name__ == "__main__":
    unittest.main()
