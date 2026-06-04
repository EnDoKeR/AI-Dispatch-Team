import csv
import json
import shutil
import unittest
from pathlib import Path

from app.document_ai.ratecon_gold_labels import (
    FIELD_DELIVERY_STOPS,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
    FIELD_TOTAL_CARRIER_RATE,
    LABEL_LABELED,
    build_gold_label_template,
)
from app.document_ai.ratecon_hybrid_contract import build_hybrid_result_template
from scripts.run_ratecon_hybrid_benchmark import run_hybrid_benchmark


REPO_ROOT = Path(__file__).resolve().parents[1]


class RateConHybridBenchmarkUncertainGoldTests(unittest.TestCase):
    def setUp(self):
        self.root = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_uncertain_gold"
        shutil.rmtree(self.root, ignore_errors=True)
        self.gold_dir = self.root / "gold"
        self.results_dir = self.root / "results"
        self.output_dir = self.root / "benchmark"
        self.gold_dir.mkdir(parents=True)
        self.results_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_gold(self, *, delivery_uncertain=True, total_rate="1700.00"):
        label = build_gold_label_template(document_id="DOC-UNCERTAIN", file_hash="hash-uncertain")
        label["label_status"] = LABEL_LABELED
        label["gold"][FIELD_LOAD_NUMBER]["value"] = "LOAD-1"
        label["gold"][FIELD_TOTAL_CARRIER_RATE]["value"] = total_rate
        label["gold"]["broker_name"]["value"] = "Broker Co"
        label["gold"]["carrier_name"]["value"] = "Carrier Co"
        label["gold"][FIELD_PICKUP_STOPS] = [
            {
                "stop_index": 1,
                "facility": "Origin Facility",
                "address": "1 Origin St",
                "city": "Hudson",
                "state": "NH",
                "zip": "03051",
                "date": "04/17/2025",
                "time": None,
                "appointment_window": "0700-1500",
                "uncertain": False,
                "notes": "",
            }
        ]
        label["gold"][FIELD_DELIVERY_STOPS] = [
            {
                "stop_index": 1,
                "facility": "Destination Facility",
                "address": "9 Destination St",
                "city": "Bay City",
                "state": "MI",
                "zip": "48706",
                "date": "04/18/2025",
                "time": None,
                "appointment_window": "0800-1700",
                "uncertain": delivery_uncertain,
                "notes": "Sanitized uncertain appointment window.",
            }
        ]
        (self.gold_dir / "doc_uncertain.gold.json").write_text(json.dumps(label), encoding="utf-8")

    def _result(self, *, rate_value="$1,700.00", delivery_city="Bay City", delivery_window="0800-1800"):
        result = build_hybrid_result_template("DOC-UNCERTAIN")
        result["evidence"] = [
            {"evidence_id": "ev_load", "field": FIELD_LOAD_NUMBER, "page": 1, "bbox": None, "text_excerpt_redacted": "<redacted>", "source": "manual"},
            {"evidence_id": "ev_rate", "field": FIELD_TOTAL_CARRIER_RATE, "page": 1, "bbox": None, "text_excerpt_redacted": "<redacted>", "source": "manual"},
            {"evidence_id": "ev_pick", "field": "pickup_stops[0]", "page": 1, "bbox": None, "text_excerpt_redacted": "<redacted>", "source": "manual"},
            {"evidence_id": "ev_del", "field": "delivery_stops[0]", "page": 1, "bbox": None, "text_excerpt_redacted": "<redacted>", "source": "manual"},
        ]
        result["fields"][FIELD_LOAD_NUMBER] = {
            "value": "LOAD-1",
            "confidence": 0.95,
            "requires_human_review": True,
            "evidence_ids": ["ev_load"],
        }
        result["fields"][FIELD_TOTAL_CARRIER_RATE] = {
            "value": rate_value,
            "currency": "USD",
            "confidence": 0.95,
            "requires_human_review": True,
            "evidence_ids": ["ev_rate"],
        }
        result["fields"][FIELD_PICKUP_STOPS][0].update(
            {
                "facility": "Origin Facility",
                "address": "1 Origin St",
                "city": "Hudson",
                "state": "NH",
                "zip": "03051",
                "date": "2025-04-17",
                "appointment_window": "0700-1500",
                "confidence": 0.9,
                "evidence_ids": ["ev_pick"],
            }
        )
        result["fields"][FIELD_DELIVERY_STOPS][0].update(
            {
                "facility": "Destination Facility",
                "address": "9 Destination St",
                "city": delivery_city,
                "state": "MI",
                "zip": "48706",
                "date": "2025-04-18",
                "appointment_window": delivery_window,
                "confidence": 0.9,
                "evidence_ids": ["ev_del"],
            }
        )
        return result

    def _write_result(self, result):
        (self.results_dir / "doc_uncertain.hybrid_result.json").write_text(json.dumps(result), encoding="utf-8")

    def test_matching_uncertain_gold_stop_is_review_required_not_unsafe_wrong(self):
        self._write_gold(delivery_uncertain=True)
        self._write_result(self._result(delivery_window="0800-1800"))

        summary = run_hybrid_benchmark(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
            write_review_packets=True,
        )

        self.assertEqual(summary["stop_metrics"][FIELD_DELIVERY_STOPS]["unsafe_wrong"], 0)
        self.assertEqual(summary["gold_uncertain_metrics"]["matches_uncertain_gold"], 1)
        self.assertEqual(summary["one_screen_summary"]["unsafe_wrong_stops"], 0)
        self.assertEqual(summary["one_screen_summary"]["gold_uncertain_review_required"], 1)
        with (self.output_dir / "hybrid_review_items.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        delivery_rows = [row for row in rows if row["field"] == FIELD_DELIVERY_STOPS]
        self.assertEqual(delivery_rows[0]["status"], "matches_uncertain_gold_review_required")
        self.assertEqual(delivery_rows[0]["recommended_action"], "needs_human_review")

    def test_stable_conflict_against_uncertain_gold_remains_unsafe_wrong(self):
        self._write_gold(delivery_uncertain=True)
        self._write_result(self._result(delivery_city="Detroit"))

        summary = run_hybrid_benchmark(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
        )

        self.assertEqual(summary["stop_metrics"][FIELD_DELIVERY_STOPS]["unsafe_wrong"], 1)
        self.assertIn("unsafe_wrong", [row["issue"] for row in summary["error_case_examples"]])

    def test_nested_manual_money_amount_matches_gold(self):
        self._write_gold(total_rate="1700.00")
        self._write_result(self._result(rate_value={"amount": "1700.0"}))

        summary = run_hybrid_benchmark(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
        )

        self.assertEqual(summary["field_metrics"][FIELD_TOTAL_CARRIER_RATE]["correct"], 1)
        self.assertEqual(summary["money_diagnostic_count"], 0)

    def test_wrong_money_diagnostics_are_redacted_by_default(self):
        self._write_gold(total_rate="1700.00")
        self._write_result(self._result(rate_value="1600.00"))

        summary = run_hybrid_benchmark(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
        )

        self.assertEqual(summary["field_metrics"][FIELD_TOTAL_CARRIER_RATE]["wrong"], 1)
        self.assertEqual(summary["money_diagnostic_count"], 1)
        with (self.output_dir / "hybrid_money_diagnostics.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["comparison_reason"], "wrong_money")
        self.assertEqual(rows[0]["hybrid_value_numeric"], "<redacted>")
        self.assertEqual(rows[0]["normalized_gold_value"], "<redacted>")


if __name__ == "__main__":
    unittest.main()
