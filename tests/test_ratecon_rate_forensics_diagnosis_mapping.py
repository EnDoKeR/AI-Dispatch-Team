import json
import unittest

from app.document_ai import rate_candidate_forensics as forensics
from app.document_ai import rate_conflict_audit as conflict_audit
from app.document_ai.ratecon_gold_labels import (
    FIELD_TOTAL_CARRIER_RATE,
    LABEL_LABELED,
    build_gold_label_template,
    evaluate_ratecon_against_gold,
)


class RateconRateForensicsDiagnosisMappingTests(unittest.TestCase):
    def _gold_label(self, *, rate_value="2500.00"):
        label = build_gold_label_template(document_id="DOC-SANITIZED-1", file_hash="hash123")
        label["file_name"] = "sanitized_ratecon.txt"
        label["file_hash"] = "hash1234567890abcdefghijklmnopqrstuvwxyz"
        label["label_status"] = LABEL_LABELED
        label["gold"][FIELD_TOTAL_CARRIER_RATE]["value"] = rate_value
        return label

    def _audit_record(self, *, selected_value="2500.00", money_context="total_carrier_pay"):
        return {
            "document_id": "DOC-SANITIZED-1",
            "file_hash": "hash1234567890abcdefghijklmnopqrstuvwxyz",
            "file_name": "sanitized_ratecon.txt",
            "legacy": {FIELD_TOTAL_CARRIER_RATE: ""},
            "shadow": {
                "resolved_fields": {
                    FIELD_TOTAL_CARRIER_RATE: {
                        "value": selected_value,
                        "confidence": 0.92,
                    }
                }
            },
            "private_eval_values": {
                "shadow_selected": {
                    FIELD_TOTAL_CARRIER_RATE: {
                        "value": selected_value,
                        "confidence": 0.92,
                        "source": "native_text",
                        "parser_name": "sanitized_rate_parser",
                        "metadata_summary": {
                            "money_context": money_context,
                            "rate_safety": "safe",
                            "document_region": "payment_summary",
                        },
                    }
                },
                "rate_money_candidate_inventory": [
                    {
                        "field": FIELD_TOTAL_CARRIER_RATE,
                        "value": selected_value,
                        "confidence": 0.92,
                        "source": "native_text",
                        "metadata_summary": {
                            "money_context": money_context,
                            "rate_safety": "safe",
                        },
                    }
                ],
            },
        }

    def test_forensics_category_and_conflict_labels_are_pinned(self):
        self.assertEqual(
            forensics.RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY,
            forensics.classify_rate_candidate_category(
                {"field_name": "total_carrier_rate", "value_type": "total_carrier_pay"}
            ),
        )
        self.assertEqual(
            forensics.RATE_CATEGORY_LINEHAUL,
            forensics.classify_rate_candidate_category(
                {"field_name": "total_carrier_rate", "value_type": "linehaul"}
            ),
        )
        self.assertEqual(
            forensics.RATE_CONFLICT_ACCESSORIAL_AS_MAIN_RATE,
            forensics.normalize_rate_conflict_reason(
                "accessorial confused with main rate"
            ),
        )
        self.assertEqual(
            "rate_source_priority_guardrails",
            forensics.recommended_rate_fix_bucket(
                forensics.RATE_CONFLICT_QUICKPAY_AS_MAIN_RATE
            ),
        )
        self.assertEqual(
            forensics.RATE_CONFLICT_UNKNOWN,
            forensics.normalize_rate_conflict_reason("new unexpected reason"),
        )

    def test_conflict_audit_reason_labels_are_pinned(self):
        self.assertEqual(
            conflict_audit.RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT,
            conflict_audit.normalize_rate_conflict_audit_reason(
                "linehaul total conflict"
            ),
        )
        self.assertEqual(
            "total_priority_over_linehaul",
            conflict_audit.recommended_rate_conflict_fix_bucket(
                conflict_audit.RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT
            ),
        )
        self.assertEqual(
            conflict_audit.RATE_EQUIVALENT_SAME_AMOUNT,
            conflict_audit.normalize_rate_candidate_equivalence_status(
                "equivalent same amount"
            ),
        )
        self.assertEqual(
            conflict_audit.RATE_AUDIT_UNKNOWN,
            conflict_audit.normalize_rate_conflict_audit_reason("new audit reason"),
        )

    def test_residual_wrong_rate_selected_safe_total_diagnosis_is_pinned(self):
        label = self._gold_label(rate_value="2600.00")
        record = self._audit_record(selected_value="2500.00")

        result = evaluate_ratecon_against_gold([label], [record])
        summary = result["residual_wrong_rate_forensics"]

        self.assertEqual(summary["wrong_selected_count"], 1)
        self.assertEqual(
            summary["diagnosis_counts"]["selected_safe_total_but_gold_differs"],
            1,
        )
        self.assertFalse(summary["cases"][0]["gold_visibility"]["gold_total_in_any_candidate"])
        self.assertNotIn("2500.00", json.dumps(summary))
        self.assertNotIn("2600.00", json.dumps(summary))

    def test_residual_wrong_rate_gold_in_candidates_not_selected_is_pinned(self):
        label = self._gold_label(rate_value="2500.00")
        record = self._audit_record(
            selected_value="2400.00",
            money_context="unknown",
        )
        record["private_eval_values"]["shadow_candidate_best"] = {
            FIELD_TOTAL_CARRIER_RATE: {
                "value": "2500.00",
                "confidence": 0.75,
                "source": "native_layout",
                "metadata_summary": {
                    "money_context": "total_carrier_pay",
                    "rate_safety": "safe",
                },
            }
        }
        record["private_eval_values"]["rate_money_candidate_inventory"].append(
            {
                "field": FIELD_TOTAL_CARRIER_RATE,
                "value": "2500.00",
                "source": "native_layout",
                "metadata_summary": {
                    "money_context": "total_carrier_pay",
                    "rate_safety": "safe",
                },
            }
        )

        result = evaluate_ratecon_against_gold([label], [record])
        summary = result["residual_wrong_rate_forensics"]

        self.assertEqual(summary["wrong_selected_count"], 1)
        self.assertEqual(
            summary["diagnosis_counts"]["gold_total_in_candidates_not_selected"],
            1,
        )
        self.assertTrue(summary["cases"][0]["gold_visibility"]["gold_total_in_any_candidate"])

    def test_wrong_reason_selected_wrong_money_context_is_pinned(self):
        label = self._gold_label(rate_value="2600.00")
        record = self._audit_record(
            selected_value="2500.00",
            money_context="total_rate",
        )

        result = evaluate_ratecon_against_gold([label], [record])
        summary = result["rate_wrong_case_summary"]

        self.assertEqual(summary["wrong_selected_count"], 1)
        self.assertEqual(summary["reason_counts"]["selected_wrong_money_context"], 1)
        self.assertEqual(summary["wrong_by_money_context"]["total_rate"], 1)
        self.assertEqual(summary["high_confidence_wrong_count"], 1)
        self.assertFalse(summary["private_values_printed"])


if __name__ == "__main__":
    unittest.main()
