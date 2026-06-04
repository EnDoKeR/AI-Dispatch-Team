import csv
import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from app.document_ai.ratecon_hybrid_contract import validate_hybrid_result
from scripts.create_ratecon_hybrid_private_manual_pilot import (
    HybridManualPilotError,
    create_private_manual_pilot,
    main,
)
from scripts.run_ratecon_hybrid_benchmark import run_hybrid_benchmark
from scripts.run_ratecon_hybrid_fixture_demo import FIXTURE_ROOT


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_private_manual_pilot"
GOLD_DIR = FIXTURE_ROOT / "gold_labels_sanitized"
AUDIT = FIXTURE_ROOT / "audit_sanitized" / "ratecon_shadow_document_pipeline_audit.jsonl"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class RateConHybridPrivateManualPilotTests(unittest.TestCase):
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
                        "--audit",
                        str(AUDIT),
                        "--gold-dir",
                        str(GOLD_DIR),
                        "--output-dir",
                        str(OUTPUT_ROOT / "pilot"),
                    ]
                )
        self.assertNotEqual(context.exception.code, 0)

    def test_refuses_output_outside_local_outputs(self):
        with self.assertRaises(HybridManualPilotError):
            create_private_manual_pilot(
                audit=AUDIT,
                gold_dir=GOLD_DIR,
                output_dir=REPO_ROOT / "tmp_manual_pilot",
            )

    def test_runs_against_sanitized_fixture_audit_and_gold(self):
        summary = create_private_manual_pilot(
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "pilot",
            max_docs=6,
        )
        self.assertEqual(summary["selected_document_count"], 6)
        self.assertEqual(summary["template_count"], 6)
        self.assertGreater(summary["checklist_row_count"], 0)
        self.assertTrue((OUTPUT_ROOT / "pilot" / "manual_pilot_summary.json").exists())
        self.assertTrue((OUTPUT_ROOT / "pilot" / "manual_pilot_readme.md").exists())
        self.assertTrue((OUTPUT_ROOT / "pilot" / "manual_pilot_checklist.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "pilot" / "manual_pilot_document_index.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "pilot" / "how_to_run_benchmark.md").exists())
        self.assertTrue((OUTPUT_ROOT / "pilot" / "templates").is_dir())

    def test_generated_templates_have_review_policy_and_no_auto_accept(self):
        create_private_manual_pilot(
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "pilot",
            max_docs=6,
        )
        for path in (OUTPUT_ROOT / "pilot" / "templates").glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            validation = validate_hybrid_result(payload, strict=False)
            self.assertTrue(validation.valid, validation.errors)
            self.assertTrue(payload["private_local_only"])
            self.assertEqual(payload["model_provider"], "manual")
            self.assertEqual(payload["model_name"], "manual_pilot_v1")
            self.assertIn("manual_pilot_unfilled", payload["review_reasons"])
            for stop_field in ("pickup_stops", "delivery_stops"):
                for stop in payload["fields"][stop_field]:
                    self.assertTrue(stop["requires_human_review"])
                    self.assertFalse(stop["auto_accept"])
                    for key in ("facility", "address", "city", "state", "zip", "date", "time", "appointment_window"):
                        self.assertIsNone(stop[key])

    def test_representative_selection_includes_different_fixture_scenarios(self):
        summary = create_private_manual_pilot(
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "pilot",
            max_docs=6,
        )
        self.assertGreaterEqual(len(summary["document_pattern_counts"]), 5)
        self.assertIn("sanitized_perfect_rate_confirmation", summary["document_pattern_counts"])
        self.assertIn("city_level_or_non_rc", summary["document_pattern_counts"])

    def test_checklist_is_excel_friendly(self):
        create_private_manual_pilot(
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "pilot",
            max_docs=2,
        )
        rows = _read_csv(OUTPUT_ROOT / "pilot" / "manual_pilot_checklist.csv")
        self.assertGreater(len(rows), 0)
        required = {
            "document_id",
            "file_name",
            "document_pattern",
            "document_type_expected",
            "field_group",
            "field_name",
            "stop_role",
            "stop_index",
            "what_to_fill",
            "evidence_required",
            "instructions",
            "common_mistakes",
            "completion_status",
        }
        self.assertTrue(required.issubset(rows[0].keys()))
        self.assertTrue(any(row["stop_role"] == "pickup" for row in rows))
        self.assertTrue(any(row["stop_role"] == "delivery" for row in rows))

    def test_benchmark_accepts_unfilled_manual_templates_with_flag(self):
        create_private_manual_pilot(
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "pilot",
            max_docs=3,
        )
        summary = run_hybrid_benchmark(
            hybrid_results_dir=OUTPUT_ROOT / "pilot" / "templates",
            gold_dir=GOLD_DIR,
            audit=AUDIT,
            output_dir=OUTPUT_ROOT / "benchmark",
            allow_unfilled_manual_templates=True,
            write_review_packets=True,
        )
        self.assertEqual(summary["schema_error_count"], 0)
        self.assertEqual(summary["unfilled_manual_template_count"], 3)
        self.assertTrue((OUTPUT_ROOT / "benchmark" / "hybrid_benchmark_report.md").exists())
        self.assertIn("allow_unfilled_manual_templates", summary)

    def test_filled_value_without_evidence_still_fails(self):
        create_private_manual_pilot(
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "pilot",
            document_ids=["DOC_FIXTURE_PERFECT"],
        )
        template_path = next((OUTPUT_ROOT / "pilot" / "templates").glob("*.json"))
        payload = json.loads(template_path.read_text(encoding="utf-8"))
        payload["fields"]["pickup_stops"][0]["city"] = "Origin City"
        template_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        summary = run_hybrid_benchmark(
            hybrid_results_dir=OUTPUT_ROOT / "pilot" / "templates",
            gold_dir=GOLD_DIR,
            audit=AUDIT,
            output_dir=OUTPUT_ROOT / "benchmark",
            allow_unfilled_manual_templates=True,
            write_review_packets=True,
        )

        self.assertGreaterEqual(summary["evidence_metrics"]["missing_evidence"], 1)
        error_rows = _read_csv(OUTPUT_ROOT / "benchmark" / "hybrid_error_cases.csv")
        self.assertTrue(any(row["issue"] == "missing_evidence" for row in error_rows))

    def test_no_external_calls_or_pdf_processing(self):
        summary = create_private_manual_pilot(
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "pilot",
            max_docs=1,
        )
        self.assertFalse(summary["external_api_calls_attempted"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["ai_model_invocation_attempted"])

    def test_generated_templates_contain_no_private_values(self):
        create_private_manual_pilot(
            audit=AUDIT,
            gold_dir=GOLD_DIR,
            output_dir=OUTPUT_ROOT / "pilot",
            max_docs=6,
        )
        template_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (OUTPUT_ROOT / "pilot" / "templates").rglob("*")
            if path.is_file()
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


if __name__ == "__main__":
    unittest.main()
