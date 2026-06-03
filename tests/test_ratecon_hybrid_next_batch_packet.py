import csv
import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from app.document_ai.ratecon_hybrid_contract import validate_hybrid_result
from scripts.create_ratecon_hybrid_next_batch_packet import (
    CHECKLIST_FIELDNAMES,
    HybridNextBatchPacketError,
    create_next_batch_packet,
    main,
)
from scripts.run_ratecon_hybrid_benchmark import run_hybrid_benchmark


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "ratecon_hybrid"
OUTPUT_ROOT = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_next_batch_packet"
PLAN = FIXTURE_ROOT / "manual_pilot_next_batch_plan.csv"
AUDIT = FIXTURE_ROOT / "audit_sanitized" / "ratecon_shadow_document_pipeline_audit.jsonl"
GOLD_DIR = FIXTURE_ROOT / "gold_labels_sanitized"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class RateConHybridNextBatchPacketTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)

    def test_script_refuses_without_confirm_private_local_run(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(
                    [
                        "--next-batch-plan",
                        str(PLAN),
                        "--audit",
                        str(AUDIT),
                        "--gold-dir",
                        str(GOLD_DIR),
                        "--output-dir",
                        str(OUTPUT_ROOT / "packet"),
                    ]
                )
        self.assertNotEqual(context.exception.code, 0)

    def test_refuses_output_outside_local_outputs(self):
        with self.assertRaises(HybridNextBatchPacketError):
            create_next_batch_packet(
                next_batch_plan=PLAN,
                audit=AUDIT,
                gold_dir=GOLD_DIR,
                output_dir=REPO_ROOT / "tmp_next_batch_packet",
            )

    def test_runs_using_sanitized_next_batch_plan(self):
        summary = create_next_batch_packet(
            next_batch_plan=PLAN,
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "packet",
            max_docs=5,
        )

        self.assertEqual(summary["selected_document_count"], 5)
        self.assertEqual(summary["template_count"], 5)
        self.assertGreater(summary["checklist_row_count"], 0)
        for name in (
            "next_batch_summary.json",
            "next_batch_readme.md",
            "next_batch_document_index.csv",
            "next_batch_checklist.csv",
            "how_to_fill_templates.md",
            "how_to_run_benchmark.md",
            "how_to_zip_for_review.md",
        ):
            self.assertTrue((OUTPUT_ROOT / "packet" / name).exists(), name)
        self.assertEqual(len(list((OUTPUT_ROOT / "packet" / "templates").glob("*.hybrid_result.json"))), 5)

    def test_generated_templates_have_review_required_and_no_auto_accept(self):
        create_next_batch_packet(
            next_batch_plan=PLAN,
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "packet",
            max_docs=5,
        )

        for path in (OUTPUT_ROOT / "packet" / "templates").glob("*.hybrid_result.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            validation = validate_hybrid_result(payload, strict=False)
            self.assertTrue(validation.valid, validation.errors)
            self.assertEqual(payload["model_provider"], "manual")
            self.assertEqual(payload["model_name"], "manual_next_batch_v1")
            self.assertTrue(payload["private_local_only"])
            self.assertIn("manual_next_batch_unfilled", payload["review_reasons"])
            for field_name in ("pickup_stops", "delivery_stops"):
                for stop in payload["fields"][field_name]:
                    self.assertTrue(stop["requires_human_review"])
                    self.assertFalse(stop["auto_accept"])
                    for key in ("facility", "address", "city", "state", "zip", "date", "time", "appointment_window"):
                        self.assertIsNone(stop[key])

    def test_generated_templates_contain_no_private_values(self):
        create_next_batch_packet(
            next_batch_plan=PLAN,
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "packet",
            max_docs=5,
        )

        template_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (OUTPUT_ROOT / "packet" / "templates").glob("*.hybrid_result.json")
        )
        banned_fragments = [
            "data/private_ratecons",
            "LoadConfirmation",
            "private_ratecon_gold_labels",
            "private_ratecon_measurement",
            "FIXLOAD-",
            "Fixture Origin Facility",
            "Correct Pickup City",
        ]
        for fragment in banned_fragments:
            self.assertNotIn(fragment, template_text)

    def test_checklist_has_expected_columns_and_evidence_rows(self):
        create_next_batch_packet(
            next_batch_plan=PLAN,
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "packet",
            max_docs=2,
        )

        rows = _read_csv(OUTPUT_ROOT / "packet" / "next_batch_checklist.csv")
        self.assertGreater(len(rows), 0)
        self.assertEqual(list(rows[0].keys()), CHECKLIST_FIELDNAMES)
        self.assertTrue(any(row["stop_role"] == "pickup" for row in rows))
        self.assertTrue(any(row["stop_role"] == "delivery" for row in rows))
        self.assertTrue(any(row["field_name"] == "evidence_page" for row in rows))
        self.assertTrue(any(row["field_name"] == "evidence_source" for row in rows))

    def test_zip_instructions_warn_not_to_include_pdfs_by_default(self):
        create_next_batch_packet(
            next_batch_plan=PLAN,
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "packet",
            max_docs=1,
        )

        text = (OUTPUT_ROOT / "packet" / "how_to_zip_for_review.md").read_text(encoding="utf-8")
        self.assertIn("Compress-Archive", text)
        self.assertIn("Do not zip PDFs unless explicitly requested", text)
        self.assertIn("Do not commit the zip", text)

    def test_benchmark_command_includes_powershell_array_form(self):
        create_next_batch_packet(
            next_batch_plan=PLAN,
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "packet",
            max_docs=1,
        )

        text = (OUTPUT_ROOT / "packet" / "how_to_run_benchmark.md").read_text(encoding="utf-8")
        self.assertIn("$benchmarkArgs = @(", text)
        self.assertIn("--allow-unfilled-manual-templates", text)

    def test_benchmark_accepts_generated_unfilled_templates(self):
        create_next_batch_packet(
            next_batch_plan=PLAN,
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "packet",
            max_docs=3,
        )

        summary = run_hybrid_benchmark(
            hybrid_results_dir=OUTPUT_ROOT / "packet" / "templates",
            gold_dir=GOLD_DIR,
            audit=AUDIT,
            output_dir=OUTPUT_ROOT / "benchmark",
            allow_unfilled_manual_templates=True,
            write_review_packets=True,
        )

        self.assertEqual(summary["schema_error_count"], 0)
        self.assertEqual(summary["unfilled_manual_template_count"], 3)
        self.assertTrue((OUTPUT_ROOT / "benchmark" / "hybrid_benchmark_report.md").exists())

    def test_filled_value_without_evidence_remains_flagged(self):
        create_next_batch_packet(
            next_batch_plan=PLAN,
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "packet",
            document_ids=["DOC_FIXTURE_PARTIAL_STOP"],
        )
        template_path = next((OUTPUT_ROOT / "packet" / "templates").glob("*.hybrid_result.json"))
        payload = json.loads(template_path.read_text(encoding="utf-8"))
        payload["fields"]["pickup_stops"][0]["city"] = "Fixture Partial City"
        template_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        summary = run_hybrid_benchmark(
            hybrid_results_dir=OUTPUT_ROOT / "packet" / "templates",
            gold_dir=GOLD_DIR,
            audit=AUDIT,
            output_dir=OUTPUT_ROOT / "benchmark",
            allow_unfilled_manual_templates=True,
            write_review_packets=True,
        )

        self.assertGreaterEqual(summary["evidence_metrics"]["missing_evidence"], 1)
        error_rows = _read_csv(OUTPUT_ROOT / "benchmark" / "hybrid_error_cases.csv")
        self.assertTrue(any(row["issue"] == "missing_evidence" for row in error_rows))

    def test_no_external_calls_pdf_processing_or_gold_edits(self):
        gold_before = {
            path.name: path.read_text(encoding="utf-8")
            for path in (GOLD_DIR).glob("*.json")
        }
        summary = create_next_batch_packet(
            next_batch_plan=PLAN,
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "packet",
            max_docs=1,
        )

        self.assertFalse(summary["external_api_calls_attempted"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["ai_model_invocation_attempted"])
        self.assertFalse(summary["gold_labels_modified"])
        gold_after = {
            path.name: path.read_text(encoding="utf-8")
            for path in (GOLD_DIR).glob("*.json")
        }
        self.assertEqual(gold_before, gold_after)


if __name__ == "__main__":
    unittest.main()
