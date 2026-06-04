import csv
import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from app.document_ai.ratecon_gold_labels import (
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_CARRIER_RATE,
    LABEL_PARTIAL,
    build_gold_label_template,
)
from app.document_ai.ratecon_hybrid_contract import build_hybrid_result_template
from scripts.create_ratecon_hybrid_scalar_discrepancy_review import (
    ScalarDiscrepancyReviewError,
    create_scalar_discrepancy_review,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class RateConHybridScalarDiscrepancyReviewTests(unittest.TestCase):
    def setUp(self):
        self.root = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_scalar_discrepancy"
        shutil.rmtree(self.root, ignore_errors=True)
        self.gold_dir = self.root / "gold"
        self.results_dir = self.root / "results"
        self.output_dir = self.root / "review"
        self.audit = self.root / "audit.jsonl"
        self.gold_dir.mkdir(parents=True)
        self.results_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_audit(self, *, document_id="DOC-1", file_name="fixture.pdf", file_hash="hash1"):
        self.audit.write_text(
            json.dumps({"document_id": document_id, "file_name": file_name, "file_hash": file_hash}) + "\n",
            encoding="utf-8",
        )

    def _gold(self, *, document_id="DOC-1", file_hash="hash1", file_name="fixture.pdf", load="LOAD-1", rate="1700.00"):
        label = build_gold_label_template(document_id=document_id, file_hash=file_hash, file_name=file_name)
        label["label_status"] = LABEL_PARTIAL
        label["gold"][FIELD_LOAD_NUMBER]["value"] = load
        label["gold"][FIELD_TOTAL_CARRIER_RATE]["value"] = rate
        return label

    def _write_gold(self, label):
        name = f"{label['document_id']}.gold.json".replace("/", "_")
        (self.gold_dir / name).write_text(json.dumps(label), encoding="utf-8")

    def _result(
        self,
        *,
        document_id="DOC-1",
        file_hash="hash1",
        file_name="fixture.pdf",
        load="LOAD-1",
        rate="1700.00",
        evidence=True,
    ):
        result = build_hybrid_result_template(document_id)
        result["file_hash"] = file_hash
        result["file_name"] = file_name
        result["document_type"] = "rate_confirmation"
        result["evidence"] = [
            {"evidence_id": "ev_load", "field": FIELD_LOAD_NUMBER, "page": 1, "bbox": None, "text_excerpt_redacted": "<redacted>", "source": "manual"},
            {"evidence_id": "ev_rate", "field": FIELD_TOTAL_CARRIER_RATE, "page": 1, "bbox": None, "text_excerpt_redacted": "<redacted>", "source": "manual"},
        ]
        result["fields"][FIELD_LOAD_NUMBER] = {
            "value": load,
            "confidence": 0.9,
            "requires_human_review": True,
            "evidence_ids": ["ev_load"] if evidence else [],
        }
        result["fields"][FIELD_TOTAL_CARRIER_RATE] = {
            "value": rate,
            "currency": "USD",
            "confidence": 0.9,
            "requires_human_review": True,
            "evidence_ids": ["ev_rate"] if evidence else [],
        }
        return result

    def _write_result(self, result, name="doc.hybrid_result.json"):
        (self.results_dir / name).write_text(json.dumps(result), encoding="utf-8")

    def _read_items(self):
        with (self.output_dir / "scalar_discrepancy_items.csv").open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_wrong_rate_creates_scalar_review_item(self):
        self._write_gold(self._gold(rate="1984.00"))
        self._write_result(self._result(rate="1700.00"))

        summary = create_scalar_discrepancy_review(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            audit=self.audit,
            output_dir=self.output_dir,
        )

        self.assertEqual(summary["discrepancy_item_count"], 1)
        item = self._read_items()[0]
        self.assertEqual(item["field"], FIELD_TOTAL_CARRIER_RATE)
        self.assertEqual(item["diagnostic_classification"], "gold_label_wrong_or_outdated")
        self.assertEqual(item["recommended_action"], "review_gold_label")

    def test_wrong_load_number_creates_scalar_review_item(self):
        self._write_gold(self._gold(load="LOAD-GOLD"))
        self._write_result(self._result(load="LOAD-HYBRID", evidence=False))

        summary = create_scalar_discrepancy_review(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
            fields=[FIELD_LOAD_NUMBER],
        )

        self.assertEqual(summary["discrepancy_item_count"], 1)
        item = self._read_items()[0]
        self.assertEqual(item["field"], FIELD_LOAD_NUMBER)
        self.assertEqual(item["diagnostic_classification"], "hybrid_template_wrong")
        self.assertEqual(item["recommended_action"], "correct_hybrid_template")

    def test_document_id_mismatch_classified(self):
        self._write_gold(self._gold(document_id="DOC-GOLD", file_hash="hash-same", file_name="gold.pdf", rate="1984.00"))
        self._write_result(self._result(document_id="DOC-HYBRID", file_hash="hash-same", file_name="hybrid.pdf", rate="1700.00"))

        create_scalar_discrepancy_review(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
            fields=[FIELD_TOTAL_CARRIER_RATE],
        )

        item = self._read_items()[0]
        self.assertEqual(item["matched_by"], "file_hash")
        self.assertEqual(item["diagnostic_classification"], "document_id_match_wrong")
        self.assertEqual(item["recommended_action"], "review_document_id_match")

    def test_file_hash_mismatch_classified(self):
        self._write_gold(self._gold(document_id="DOC-1", file_hash="hash-gold", rate="1984.00"))
        self._write_result(self._result(document_id="DOC-1", file_hash="hash-hybrid", rate="1700.00"))

        create_scalar_discrepancy_review(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
            fields=[FIELD_TOTAL_CARRIER_RATE],
        )

        item = self._read_items()[0]
        self.assertEqual(item["matched_by"], "document_id")
        self.assertEqual(item["diagnostic_classification"], "file_hash_match_wrong")
        self.assertEqual(item["recommended_action"], "review_file_hash_match")

    def test_matching_normalized_money_does_not_create_discrepancy(self):
        self._write_gold(self._gold(rate="1700.00"))
        for index, value in enumerate(["$1,700.00", "1700", 1700.0], start=1):
            self._write_result(self._result(document_id=f"DOC-{index}", file_hash=f"hash{index}", rate=value), f"doc{index}.json")
            self._write_gold(self._gold(document_id=f"DOC-{index}", file_hash=f"hash{index}", rate="1700.00"))

        summary = create_scalar_discrepancy_review(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
            fields=[FIELD_TOTAL_CARRIER_RATE],
        )

        self.assertEqual(summary["discrepancy_item_count"], 0)

    def test_private_values_redacted_by_default(self):
        self._write_gold(self._gold(rate="1984.00"))
        self._write_result(self._result(rate="1700.00"))

        create_scalar_discrepancy_review(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
        )

        item = self._read_items()[0]
        self.assertEqual(item["hybrid_value_normalized"], "<redacted>")
        self.assertEqual(item["gold_value_local_only"], "<redacted>")

    def test_private_values_included_only_with_flag(self):
        self._write_gold(self._gold(rate="1984.00"))
        self._write_result(self._result(rate="1700.00"))

        create_scalar_discrepancy_review(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
            include_private_values_local_only=True,
        )

        item = self._read_items()[0]
        self.assertEqual(item["hybrid_value_normalized"], "1700.00")
        self.assertEqual(item["gold_value_normalized"], "1984.00")

    def test_patch_template_has_blank_proposed_values(self):
        self._write_gold(self._gold(rate="1984.00"))
        self._write_result(self._result(rate="1700.00"))

        summary = create_scalar_discrepancy_review(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
        )

        template = json.loads((self.output_dir / "scalar_discrepancy_patch_template.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["patch_template_row_count"], 1)
        self.assertEqual(template["planned_change_count"], 0)
        self.assertIsNone(template["patches"][0]["proposed_hybrid_value"])
        self.assertIsNone(template["patches"][0]["proposed_gold_value"])

    def test_refuses_without_confirm_private_local_run(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(
                    [
                        "--hybrid-results-dir",
                        str(self.results_dir),
                        "--gold-dir",
                        str(self.gold_dir),
                    ]
                )

        self.assertNotEqual(context.exception.code, 0)

    def test_refuses_output_outside_local_outputs(self):
        self._write_gold(self._gold(rate="1984.00"))
        self._write_result(self._result(rate="1700.00"))

        with self.assertRaises(ScalarDiscrepancyReviewError):
            create_scalar_discrepancy_review(
                hybrid_results_dir=self.results_dir,
                gold_dir=self.gold_dir,
                output_dir=REPO_ROOT / "tmp_scalar_review",
            )

    def test_no_external_calls_and_no_gold_or_template_edits(self):
        gold = self._gold(rate="1984.00")
        self._write_gold(gold)
        result = self._result(rate="1700.00")
        self._write_result(result)
        gold_before = (self.gold_dir / "DOC-1.gold.json").read_text(encoding="utf-8")
        result_before = (self.results_dir / "doc.hybrid_result.json").read_text(encoding="utf-8")

        summary = create_scalar_discrepancy_review(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
        )

        self.assertFalse(summary["external_api_calls_attempted"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ai_model_invocation_attempted"])
        self.assertEqual((self.gold_dir / "DOC-1.gold.json").read_text(encoding="utf-8"), gold_before)
        self.assertEqual((self.results_dir / "doc.hybrid_result.json").read_text(encoding="utf-8"), result_before)


if __name__ == "__main__":
    unittest.main()
