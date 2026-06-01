import json
import tempfile
from pathlib import Path
import unittest

from app.document_ai.ratecon_gold_labels import (
    ACTION_SHADOW_EXPERIMENT,
    ADJ_SHADOW_CORRECT_LEGACY_WRONG,
    FIELD_BROKER_NAME,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_CARRIER_RATE,
    LABEL_LABELED,
    SYSTEM_LEGACY,
    SYSTEM_SHADOW,
    build_gold_label_template,
    evaluate_ratecon_against_gold,
)
from scripts.evaluate_ratecon_against_gold import evaluate_and_write


class EvaluateRateconAgainstGoldTests(unittest.TestCase):
    def _gold_label(self):
        label = build_gold_label_template(document_id="DOC-1", file_hash="hash123")
        label["file_name"] = "LoadConfirmation1.pdf"
        label["file_hash"] = "hash1234567890abcdefghijklmnopqrstuvwxyz"
        label["label_status"] = LABEL_LABELED
        label["gold"][FIELD_LOAD_NUMBER]["value"] = "LOAD-123"
        label["gold"][FIELD_TOTAL_CARRIER_RATE]["value"] = "2500.00"
        label["gold"][FIELD_BROKER_NAME]["value"] = "Acme Logistics LLC"
        label["gold"]["carrier_name"]["value"] = "Carrier Co"
        label["gold"]["pickup_stops"] = [
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
        label["gold"]["delivery_stops"] = [
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

    def _audit_record(self):
        return {
            "document_id": "RATECON_001",
            "file_hash": "hash1234567890abcd",
            "file_name": "LoadConfirmation1.pdf",
            "legacy": {
                "load_number": "WRONG",
                "total_carrier_rate": "2500",
                "broker_name": "Acme Logistics",
                "carrier_name": "Carrier Company",
                "pickup_count": 1,
                "delivery_count": 0,
            },
            "shadow": {
                "resolved_fields": {
                    "load_number": {"value": "load123", "confidence": 0.86},
                    "total_carrier_rate": {"value": "$2,500.00", "confidence": 0.65},
                    "broker_name": {"value": "", "confidence": 0.0},
                    "carrier_name": {"value": "Carrier Co", "confidence": 0.91},
                    "pickup_stops": {
                        "value": [{"city": "Dallas", "state": "TX"}],
                        "confidence": 0.62,
                    },
                    "delivery_stops": {"value": "", "confidence": 0.0},
                },
                "resolver_decision_traces": {
                    "load_number": {
                        "selected_candidate": {"value": "load123", "confidence": 0.86}
                    }
                },
            },
        }

    def test_evaluate_compares_legacy_and_shadow_side_by_side(self):
        label = self._gold_label()
        label["document_id"] = "LoadConfirmation1"
        label["file_name"] = "LoadConfirmation1.pdf"
        label["file_hash"] = "hash1234567890abcdefghijklmnopqrstuvwxyz"

        result = evaluate_ratecon_against_gold([label], [self._audit_record()])

        self.assertEqual(result["labels_evaluated"], 1)
        self.assertEqual(result["labels_matched_to_audit"], 1)
        legacy_load = result["field_metrics"][SYSTEM_LEGACY][FIELD_LOAD_NUMBER]
        shadow_load = result["field_metrics"][SYSTEM_SHADOW][FIELD_LOAD_NUMBER]
        self.assertEqual(legacy_load["wrong_value_count"], 1)
        self.assertEqual(shadow_load["normalized_match_count"], 1)
        self.assertEqual(
            result["adjudication"]["recommended_action_counts"][ACTION_SHADOW_EXPERIMENT],
            2,
        )
        self.assertEqual(
            result["document_metrics"][0]["field_results"][FIELD_LOAD_NUMBER][
                "adjudication_category"
            ],
            ADJ_SHADOW_CORRECT_LEGACY_WRONG,
        )

    def test_evaluate_derived_stop_component_fields(self):
        label = self._gold_label()
        record = self._audit_record()
        record["shadow"]["resolved_fields"]["pickup_stops"] = {
            "value": [
                {
                    "city": "Dallas",
                    "state": "TX",
                    "date": "2026-01-02",
                }
            ],
            "confidence": 0.72,
        }

        result = evaluate_ratecon_against_gold([label], [record])

        shadow_location = result["field_metrics"][SYSTEM_SHADOW][FIELD_PICKUP_LOCATION]
        shadow_date = result["field_metrics"][SYSTEM_SHADOW][FIELD_PICKUP_DATE]
        self.assertEqual(shadow_location["exact_match_count"], 1)
        self.assertEqual(shadow_date["normalized_match_count"], 1)

    def test_confidence_calibration_counts_low_confidence_correct(self):
        result = evaluate_ratecon_against_gold([self._gold_label()], [self._audit_record()])

        rate = result["field_metrics"][SYSTEM_SHADOW][FIELD_TOTAL_CARRIER_RATE]

        self.assertEqual(rate["low_confidence_but_correct_count"], 1)
        self.assertTrue(
            result["confidence_calibration"][FIELD_TOTAL_CARRIER_RATE][
                "do_not_apply_automatically"
            ]
        )

    def test_evaluator_writes_safe_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            gold_dir = Path(tmp) / "gold"
            gold_dir.mkdir()
            (gold_dir / "doc1.json").write_text(
                json.dumps(self._gold_label()),
                encoding="utf-8",
            )
            audit = Path(tmp) / "audit.jsonl"
            audit.write_text(json.dumps(self._audit_record()) + "\n", encoding="utf-8")
            output = Path(tmp) / "eval"

            result = evaluate_and_write(
                gold_path=gold_dir,
                audit_path=audit,
                output_dir=output,
                allow_custom_output_dir=True,
            )

            self.assertEqual(result["labels_evaluated"], 1)
            self.assertEqual(result["labels_matched_to_audit"], 1)
            self.assertTrue((output / "ratecon_gold_evaluation_summary.json").exists())
            report = (output / "ratecon_gold_evaluation_report.md").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("load123", report)
            self.assertIn("do_not_apply_automatically=True", report)
            document_metrics = (output / "ratecon_gold_document_metrics.csv").read_text(
                encoding="utf-8"
            )
            self.assertIn("adjudication_category", document_metrics)


if __name__ == "__main__":
    unittest.main()
