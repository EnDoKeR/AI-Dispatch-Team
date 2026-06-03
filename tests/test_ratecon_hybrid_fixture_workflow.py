import csv
import shutil
import unittest
from pathlib import Path

from app.document_ai.ratecon_gold_labels import (
    FIELD_DELIVERY_STOPS,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
    FIELD_TOTAL_CARRIER_RATE,
)
from scripts.run_ratecon_hybrid_fixture_demo import FIXTURE_ROOT, run_fixture_demo


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_fixture_demo"
EXPECTED_REVIEW_COLUMNS = {
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
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class RateConHybridFixtureWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
        cls.summary = run_fixture_demo(OUTPUT_DIR)
        cls.field_rows = _read_csv(OUTPUT_DIR / "hybrid_field_metrics.csv")
        cls.error_rows = _read_csv(OUTPUT_DIR / "hybrid_error_cases.csv")
        cls.review_rows = _read_csv(OUTPUT_DIR / "hybrid_review_items.csv")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

    def test_sanitized_fixture_files_exist(self):
        self.assertTrue((FIXTURE_ROOT / "README.md").exists())
        self.assertTrue((FIXTURE_ROOT / "gold_labels_sanitized").is_dir())
        self.assertTrue((FIXTURE_ROOT / "hybrid_results_sanitized").is_dir())
        self.assertTrue((FIXTURE_ROOT / "audit_sanitized" / "ratecon_shadow_document_pipeline_audit.jsonl").exists())
        self.assertGreaterEqual(len(list((FIXTURE_ROOT / "gold_labels_sanitized").glob("*.json"))), 6)
        self.assertGreaterEqual(len(list((FIXTURE_ROOT / "hybrid_results_sanitized").glob("*.json"))), 6)

    def test_fixture_demo_runs_and_writes_report_summary(self):
        self.assertEqual(self.summary["hybrid_result_count"], 6)
        self.assertTrue((OUTPUT_DIR / "hybrid_benchmark_summary.json").exists())
        self.assertTrue((OUTPUT_DIR / "hybrid_benchmark_report.md").exists())
        report = (OUTPUT_DIR / "hybrid_benchmark_report.md").read_text(encoding="utf-8")
        self.assertIn("## One-Screen Summary", report)
        self.assertIn("## Safety", report)
        self.assertIn("## Error Case Examples", report)
        self.assertIn("## Next Action", report)

    def test_review_csv_has_expected_columns(self):
        with (OUTPUT_DIR / "hybrid_review_items.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            self.assertTrue(EXPECTED_REVIEW_COLUMNS.issubset(set(reader.fieldnames or [])))

    def test_perfect_fixture_scores_correctly(self):
        perfect_rows = [row for row in self.field_rows if row["document_id"] == "DOC_FIXTURE_PERFECT"]
        by_field = {row["field"]: row for row in perfect_rows if row["field"] in {FIELD_LOAD_NUMBER, FIELD_TOTAL_CARRIER_RATE}}
        self.assertIn(by_field[FIELD_LOAD_NUMBER]["status"], {"correct_exact", "correct_normalized"})
        self.assertIn(by_field[FIELD_TOTAL_CARRIER_RATE]["status"], {"correct_exact", "correct_normalized"})
        stop_rows = {(row["field"], row["stop_index"]): row for row in perfect_rows if row["field"] in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}}
        self.assertEqual(stop_rows[(FIELD_PICKUP_STOPS, "1")]["tier"], "exact_complete")
        self.assertEqual(stop_rows[(FIELD_DELIVERY_STOPS, "1")]["tier"], "exact_complete")

    def test_missing_evidence_fixture_reports_missing_evidence(self):
        self.assertTrue(
            any(
                row["document_id"] == "DOC_FIXTURE_MISSING_EVIDENCE"
                and row["issue"] == "missing_evidence"
                for row in self.error_rows
            )
        )
        self.assertTrue(
            any(
                row["document_id"] == "DOC_FIXTURE_MISSING_EVIDENCE"
                and row["missing_evidence"] == "True"
                for row in self.review_rows
            )
        )

    def test_unsafe_wrong_stop_fixture_reports_unsafe_wrong(self):
        self.assertTrue(
            any(
                row["document_id"] == "DOC_FIXTURE_UNSAFE_WRONG_STOP"
                and row["issue"] == "unsafe_wrong"
                for row in self.error_rows
            )
        )
        self.assertTrue(
            any(
                row["document_id"] == "DOC_FIXTURE_UNSAFE_WRONG_STOP"
                and row["status"] == "unsafe_wrong"
                for row in self.review_rows
            )
        )

    def test_auto_accept_fixture_reports_violation(self):
        self.assertEqual(self.summary["review_policy"]["stop_auto_accept_violation"], 1)
        self.assertTrue(
            any(
                row["document_id"] == "DOC_FIXTURE_AUTO_ACCEPT"
                and row["auto_accept_violation"] == "True"
                for row in self.review_rows
            )
        )

    def test_non_rc_fixture_is_classified_separately(self):
        self.assertEqual(self.summary["document_classification"]["non_rc_bol_pod_filtered"], 1)

    def test_no_external_calls(self):
        self.assertFalse(self.summary["external_api_calls_attempted"])
        self.assertFalse(self.summary["pdf_processing_attempted"])
        self.assertFalse(self.summary["ai_model_invocation_attempted"])

    def test_no_private_values_in_fixtures_or_default_output(self):
        banned_fragments = [
            "data/private_ratecons",
            "LoadConfirmation",
            "private_ratecon_gold_labels",
            "private_ratecon_measurement",
        ]
        fixture_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in FIXTURE_ROOT.rglob("*")
            if path.is_file()
        )
        output_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in OUTPUT_DIR.rglob("*")
            if path.is_file()
        )
        for fragment in banned_fragments:
            self.assertNotIn(fragment, fixture_text)
            self.assertNotIn(fragment, output_text)
        self.assertNotIn('"raw_text_local_only": "', fixture_text)


if __name__ == "__main__":
    unittest.main()
