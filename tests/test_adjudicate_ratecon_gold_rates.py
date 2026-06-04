import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.ratecon_gold_labels import (
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_CARRIER_RATE,
    LABEL_LABELED,
    build_gold_label_template,
)
from scripts.adjudicate_ratecon_gold_rates import (
    _candidate_values_summary,
    _recommend_gold_value,
    apply_high_confidence_recommendations,
    build_adjudication_review,
    run_adjudication,
)


class AdjudicateRateconGoldRatesTests(unittest.TestCase):
    def _gold_label(self, value="2500.00", document_id="DOC-1", file_name="LoadConfirmation1.pdf"):
        label = build_gold_label_template(
            document_id=document_id,
            file_hash=f"{document_id.lower()}hash1234567890",
            file_name=file_name,
        )
        label["label_status"] = LABEL_LABELED
        label["gold"][FIELD_LOAD_NUMBER]["value"] = "LOAD-1"
        label["gold"][FIELD_TOTAL_CARRIER_RATE]["value"] = value
        label["gold"][FIELD_BROKER_NAME]["value"] = "Broker Co"
        label["gold"][FIELD_CARRIER_NAME]["value"] = "Carrier Co"
        label["gold"]["pickup_stops"] = [{"stop_index": 1, "city": "Dallas"}]
        label["gold"]["delivery_stops"] = [{"stop_index": 1, "city": "Houston"}]
        return label

    def _audit_record(
        self,
        selected_value="2400.00",
        selected_context="total_carrier_pay",
        inventory=None,
        document_id="DOC-1",
        file_name="LoadConfirmation1.pdf",
    ):
        return {
            "document_id": document_id,
            "file_hash": f"{document_id.lower()}hash1234567890",
            "file_name": file_name,
            "private_eval_values": {
                "shadow_selected": {
                    FIELD_TOTAL_CARRIER_RATE: {
                        "value": selected_value,
                        "confidence": 0.91,
                        "source": "native_layout",
                        "metadata_summary": {
                            "money_context": selected_context,
                            "rate_safety": "safe",
                            "document_region": "payment_summary",
                        },
                    },
                    FIELD_LOAD_NUMBER: {"value": "LOAD-1", "confidence": 0.95},
                },
                "rate_money_candidate_inventory": inventory
                if inventory is not None
                else [
                    self._rate_candidate("2400.00", "total_carrier_pay"),
                    self._rate_candidate("2500.00", "carrier_freight_pay"),
                ],
            },
        }

    def _rate_candidate(self, value, context, safety="safe"):
        return {
            "field": FIELD_TOTAL_CARRIER_RATE,
            "value": value,
            "confidence": 0.8,
            "metadata_summary": {
                "money_context": context,
                "rate_safety": safety,
            },
        }

    def test_recommendation_prefers_nonblank_total_carrier_pay_over_freight_pay_gold(self):
        label = self._gold_label("2500.00")
        record = self._audit_record()

        review = build_adjudication_review([label], [record])

        self.assertEqual(review["case_count"], 1)
        case = review["cases"][0]
        self.assertEqual(case["recommended_gold_value"], "2400.00")
        self.assertEqual(
            case["recommendation_reason"],
            "nonblank_total_carrier_pay_over_carrier_freight_pay",
        )
        self.assertEqual(case["confidence"], "high")
        self.assertFalse(case["needs_manual_review"])

    def test_blank_total_carrier_pay_keeps_carrier_freight_pay_as_valid_gold(self):
        inventory = [
            self._rate_candidate("", "total_carrier_pay"),
            self._rate_candidate("2200.00", "carrier_freight_pay"),
        ]
        record = self._audit_record(
            selected_value="2300.00",
            selected_context="total_carrier_pay",
            inventory=inventory,
        )
        summary = _candidate_values_summary(record, "2200.00", "2300.00")

        recommendation = _recommend_gold_value(
            {"diagnosis": "selected_safe_total_but_gold_differs", "selected_rate": {"money_context": "total_carrier_pay"}},
            summary,
            "2200.00",
            "2300.00",
        )

        self.assertEqual(
            recommendation["recommendation_reason"],
            "blank_total_carrier_pay_valid_carrier_freight_fallback",
        )
        self.assertEqual(recommendation["recommended_gold_value"], "2200.00")
        self.assertFalse(recommendation["needs_manual_review"])

    def test_dry_run_writes_review_without_modifying_gold_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gold_dir = root / ".local_outputs" / "gold"
            gold_dir.mkdir(parents=True)
            gold_path = gold_dir / "LoadConfirmation1.gold.json"
            original = self._gold_label("2500.00")
            gold_path.write_text(json.dumps(original), encoding="utf-8")
            audit_path = root / "audit.jsonl"
            audit_path.write_text(json.dumps(self._audit_record()) + "\n", encoding="utf-8")
            output_dir = root / ".local_outputs" / "adjudication"

            result = run_adjudication(
                gold_dir=gold_dir,
                audit=audit_path,
                output_dir=output_dir,
                apply=False,
            )

            self.assertEqual(result["case_count"], 1)
            self.assertEqual(result["applied_change_count"], 0)
            self.assertTrue((output_dir / "rate_gold_adjudication_review.json").exists())
            after = json.loads(gold_path.read_text(encoding="utf-8"))
            self.assertEqual(after["gold"][FIELD_TOTAL_CARRIER_RATE]["value"], "2500.00")

    def test_apply_changes_only_high_confidence_local_gold_labels_and_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gold_dir = root / ".local_outputs" / "gold"
            gold_dir.mkdir(parents=True)
            gold_path = gold_dir / "LoadConfirmation1.gold.json"
            gold_path.write_text(json.dumps(self._gold_label("2500.00")), encoding="utf-8")
            audit_path = root / "audit.jsonl"
            audit_path.write_text(json.dumps(self._audit_record()) + "\n", encoding="utf-8")
            output_dir = root / ".local_outputs" / "adjudication"

            result = run_adjudication(
                gold_dir=gold_dir,
                audit=audit_path,
                output_dir=output_dir,
                apply=True,
            )

            self.assertEqual(result["applied_change_count"], 1)
            updated = json.loads(gold_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["gold"][FIELD_TOTAL_CARRIER_RATE]["value"], "2400.00")
            self.assertTrue((output_dir / "applied_gold_rate_changes.json").exists())

    def test_apply_refuses_unsafe_gold_dir_without_confirmation(self):
        review = {
            "cases": [
                {
                    "file_name": "LoadConfirmation1.pdf",
                    "confidence": "high",
                    "needs_manual_review": False,
                    "recommended_gold_value": "2400.00",
                    "current_gold_total_carrier_rate": "2500.00",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            gold_dir = Path(tmp) / "gold"
            gold_dir.mkdir()

            with self.assertRaises(ValueError):
                apply_high_confidence_recommendations(gold_dir, review)

    def test_grand_total_over_linehaul_recommendation_is_high_confidence(self):
        label = self._gold_label("3150.00")
        record = self._audit_record(
            selected_value="3600.00",
            selected_context="total_rate",
            inventory=[
                self._rate_candidate("3150.00", "linehaul_total"),
                self._rate_candidate("3600.00", "total_rate"),
            ],
        )

        review = build_adjudication_review([label], [record])

        case = review["cases"][0]
        self.assertEqual(case["recommended_gold_value"], "3600.00")
        self.assertEqual(case["recommendation_reason"], "full_total_over_linehaul_component")
        self.assertEqual(case["confidence"], "high")


if __name__ == "__main__":
    unittest.main()
