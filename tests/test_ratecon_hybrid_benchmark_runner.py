import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
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
from scripts.run_ratecon_hybrid_benchmark import (
    HybridBenchmarkError,
    main,
    run_hybrid_benchmark,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class RateConHybridBenchmarkRunnerTests(unittest.TestCase):
    def setUp(self):
        self.root = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_benchmark"
        shutil.rmtree(self.root, ignore_errors=True)
        self.gold_dir = self.root / "gold"
        self.results_dir = self.root / "results"
        self.output_dir = self.root / "benchmark"
        self.gold_dir.mkdir(parents=True)
        self.results_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _gold_label(self):
        label = build_gold_label_template(document_id="DOC-1", file_hash="hash123")
        label["label_status"] = LABEL_LABELED
        label["gold"][FIELD_LOAD_NUMBER]["value"] = "LOAD-123"
        label["gold"][FIELD_TOTAL_CARRIER_RATE]["value"] = "2500.00"
        label["gold"]["broker_name"]["value"] = "Broker Co"
        label["gold"]["carrier_name"]["value"] = "Carrier Co"
        label["gold"][FIELD_PICKUP_STOPS] = [
            {
                "stop_index": 1,
                "facility": None,
                "address": None,
                "city": "Dallas",
                "state": "TX",
                "zip": None,
                "date": "01/02/2026",
                "time": None,
                "appointment_window": None,
                "uncertain": False,
                "notes": "",
            }
        ]
        label["gold"][FIELD_DELIVERY_STOPS] = [
            {
                "stop_index": 1,
                "facility": None,
                "address": None,
                "city": "Houston",
                "state": "TX",
                "zip": None,
                "date": "01/03/2026",
                "time": None,
                "appointment_window": None,
                "uncertain": False,
                "notes": "",
            }
        ]
        return label

    def _write_gold(self):
        (self.gold_dir / "doc1.gold.json").write_text(
            json.dumps(self._gold_label()),
            encoding="utf-8",
        )

    def _valid_result(self):
        result = build_hybrid_result_template("DOC-1")
        result["evidence"] = [
            {
                "evidence_id": "ev_load",
                "field": "load_number",
                "page": 1,
                "bbox": None,
                "text_excerpt_redacted": "<redacted>",
                "source": "model",
            },
            {
                "evidence_id": "ev_rate",
                "field": "total_carrier_rate",
                "page": 1,
                "bbox": None,
                "text_excerpt_redacted": "<redacted>",
                "source": "model",
            },
            {
                "evidence_id": "ev_pick",
                "field": "pickup_stops[0]",
                "page": 1,
                "bbox": None,
                "text_excerpt_redacted": "<redacted>",
                "source": "model",
            },
            {
                "evidence_id": "ev_del",
                "field": "delivery_stops[0]",
                "page": 1,
                "bbox": None,
                "text_excerpt_redacted": "<redacted>",
                "source": "model",
            },
        ]
        result["fields"]["load_number"] = {
            "value": "load123",
            "confidence": 0.91,
            "requires_human_review": True,
            "evidence_ids": ["ev_load"],
        }
        result["fields"]["total_carrier_rate"] = {
            "value": "$2,500.00",
            "currency": "USD",
            "confidence": 0.88,
            "requires_human_review": True,
            "evidence_ids": ["ev_rate"],
        }
        result["fields"]["pickup_stops"][0].update(
            {
                "city": "Dallas",
                "date": "2026-01-02",
                "confidence": 0.82,
                "evidence_ids": ["ev_pick"],
            }
        )
        result["fields"]["delivery_stops"][0].update(
            {
                "city": "Austin",
                "state": "TX",
                "date": "2026-01-03",
                "confidence": 0.84,
                "evidence_ids": ["ev_del"],
            }
        )
        return result

    def _write_result(self, result):
        (self.results_dir / "doc1.hybrid_result.json").write_text(
            json.dumps(result),
            encoding="utf-8",
        )

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
        self._write_gold()
        self._write_result(self._valid_result())

        with self.assertRaises(HybridBenchmarkError):
            run_hybrid_benchmark(
                hybrid_results_dir=self.results_dir,
                gold_dir=self.gold_dir,
                output_dir=REPO_ROOT / "tmp_hybrid_benchmark",
            )

    def test_computes_load_rate_and_stop_metrics(self):
        self._write_gold()
        self._write_result(self._valid_result())

        summary = run_hybrid_benchmark(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
            strict_schema=True,
        )

        self.assertEqual(summary["schema_error_count"], 0)
        self.assertEqual(summary["field_metrics"][FIELD_LOAD_NUMBER]["correct"], 1)
        self.assertEqual(summary["field_metrics"][FIELD_TOTAL_CARRIER_RATE]["correct"], 1)
        self.assertEqual(summary["stop_metrics"][FIELD_PICKUP_STOPS]["dispatch_usable"], 1)
        self.assertEqual(summary["stop_metrics"][FIELD_DELIVERY_STOPS]["unsafe_wrong"], 1)
        self.assertTrue((self.output_dir / "hybrid_benchmark_summary.json").exists())
        self.assertTrue((self.output_dir / "hybrid_field_metrics.csv").exists())
        self.assertTrue((self.output_dir / "hybrid_document_metrics.csv").exists())
        self.assertTrue((self.output_dir / "hybrid_error_cases.csv").exists())
        self.assertTrue((self.output_dir / "hybrid_schema_errors.csv").exists())

    def test_detects_schema_errors_auto_accept_and_missing_evidence(self):
        self._write_gold()
        result = self._valid_result()
        result["fields"]["pickup_stops"][0]["auto_accept"] = True
        result["fields"]["delivery_stops"][0]["evidence_ids"] = []
        result["fields"]["delivery_stops"][0]["evidence_page"] = None
        self._write_result(result)

        summary = run_hybrid_benchmark(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
        )

        self.assertGreaterEqual(summary["schema_error_count"], 1)
        self.assertEqual(summary["review_policy"]["stop_auto_accept_violation"], 1)
        self.assertGreaterEqual(summary["evidence_metrics"]["missing_evidence"], 1)

    def test_writes_review_packet_when_requested(self):
        self._write_gold()
        self._write_result(self._valid_result())

        run_hybrid_benchmark(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
            write_review_packets=True,
        )

        self.assertTrue((self.output_dir / "hybrid_review_packet.json").exists())
        self.assertTrue((self.output_dir / "hybrid_review_items.csv").exists())
        self.assertTrue((self.output_dir / "hybrid_review_packet.md").exists())

    def test_no_external_api_calls_in_summary(self):
        self._write_gold()
        self._write_result(self._valid_result())

        summary = run_hybrid_benchmark(
            hybrid_results_dir=self.results_dir,
            gold_dir=self.gold_dir,
            output_dir=self.output_dir,
        )

        self.assertFalse(summary["external_api_calls_attempted"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ai_model_invocation_attempted"])

    def test_local_outputs_ignored(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn(".local_outputs/", gitignore)
        self.assertIn(".local_outputs/**", gitignore)


if __name__ == "__main__":
    unittest.main()
