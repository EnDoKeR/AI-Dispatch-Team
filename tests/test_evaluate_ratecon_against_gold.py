import json
import tempfile
from pathlib import Path
import hashlib
import unittest

from app.document_ai.ratecon_gold_labels import (
    ACTION_SHADOW_EXPERIMENT,
    ADJ_SHADOW_CORRECT_LEGACY_WRONG,
    FIELD_BROKER_NAME,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_CARRIER_RATE,
    LABEL_LABELED,
    LABEL_SKIPPED,
    SYSTEM_LEGACY,
    SYSTEM_SHADOW,
    SYSTEM_SHADOW_BEST_INDEPENDENT,
    SYSTEM_SHADOW_BEST_LAYOUT,
    SYSTEM_SHADOW_CANDIDATE_BEST,
    build_gold_label_template,
    evaluate_ratecon_against_gold,
)
from scripts.evaluate_ratecon_against_gold import evaluate_and_write
from scripts.compare_ratecon_gold_evaluations import compare_profiles, compare_summaries


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

    def test_legacy_redacted_value_is_not_counted_as_extractor_missing(self):
        label = self._gold_label()
        record = self._audit_record()
        record["legacy"] = {
            "load_number": "",
            "fields_present": ["load_number"],
            "pickup_count": 0,
            "delivery_count": 0,
        }

        result = evaluate_ratecon_against_gold([label], [record])

        legacy_load = result["field_metrics"][SYSTEM_LEGACY][FIELD_LOAD_NUMBER]
        self.assertEqual(legacy_load["missing_count"], 0)
        self.assertEqual(legacy_load["field_not_serialized_count"], 1)

    def test_private_eval_legacy_value_is_evaluated_when_available(self):
        label = self._gold_label()
        record = self._audit_record()
        record["legacy"] = {
            "load_number": "",
            "fields_present": ["load_number"],
            "pickup_count": 0,
            "delivery_count": 0,
        }
        record["private_eval_values"] = {
            "legacy_selected": {
                FIELD_LOAD_NUMBER: {
                    "value": "LOAD-123",
                    "source": "legacy_measurement_resolution",
                }
            }
        }

        result = evaluate_ratecon_against_gold([label], [record])

        legacy_load = result["field_metrics"][SYSTEM_LEGACY][FIELD_LOAD_NUMBER]
        self.assertEqual(legacy_load["exact_match_count"], 1)
        self.assertEqual(legacy_load["field_not_serialized_count"], 0)

    def test_private_eval_stop_components_are_comparable(self):
        label = self._gold_label()
        record = self._audit_record()
        record["private_eval_values"] = {
            "shadow_selected": {
                "pickup_stops": {
                    "value": [
                        {
                            "role": "pickup",
                            "stop_index": 1,
                            "city": "Dallas",
                            "state": "TX",
                            "date": "2026-01-02",
                            "time": "08:00",
                        }
                    ],
                    "confidence": 0.74,
                    "source": "stop_evidence_assembler",
                    "component_values_serialized": True,
                },
                "delivery_stops": {
                    "value": [
                        {
                            "role": "delivery",
                            "stop_index": 1,
                            "city": "Houston",
                            "state": "TX",
                            "date": "2026-01-03",
                        }
                    ],
                    "confidence": 0.74,
                    "source": "stop_evidence_assembler",
                    "component_values_serialized": True,
                },
            }
        }

        result = evaluate_ratecon_against_gold([label], [record])

        self.assertEqual(
            result["field_metrics"][SYSTEM_SHADOW][FIELD_PICKUP_LOCATION]["exact_match_count"],
            1,
        )
        self.assertEqual(
            result["field_metrics"][SYSTEM_SHADOW][FIELD_PICKUP_DATE]["normalized_match_count"],
            1,
        )
        self.assertEqual(
            result["field_metrics"][SYSTEM_SHADOW][FIELD_DELIVERY_LOCATION]["exact_match_count"],
            1,
        )
        self.assertEqual(
            result["field_metrics"][SYSTEM_SHADOW][FIELD_DELIVERY_DATE]["normalized_match_count"],
            1,
        )

    def test_load_candidate_recall_counts_gold_in_candidate_inventory(self):
        label = self._gold_label()
        record = self._audit_record()
        record["private_eval_values"] = {
            "load_identity_candidate_inventory": [
                {
                    "field": "load_number",
                    "value": "LOAD-123",
                    "independent": True,
                    "layout_based": True,
                    "header_candidate": True,
                    "table_based": False,
                    "legacy_fallback": False,
                }
            ],
            "load_visibility_probe": {},
        }

        result = evaluate_ratecon_against_gold([label], [record])
        recall = result["load_candidate_recall_summary"]

        self.assertEqual(recall["evaluated_docs"], 1)
        self.assertEqual(recall["gold_load_in_any_candidate"], 1)
        self.assertEqual(recall["gold_load_in_independent_candidate"], 1)
        self.assertEqual(recall["gold_load_in_layout_candidate"], 1)
        self.assertEqual(recall["gold_load_in_header_candidate"], 1)
        self.assertEqual(recall["gold_load_not_in_candidates"], 0)

    def test_load_candidate_recall_counts_gold_visible_in_text_but_not_candidate(self):
        label = self._gold_label()
        record = self._audit_record()
        digest = hashlib.sha256("load123".encode("utf-8")).hexdigest()
        record["private_eval_values"] = {
            "load_identity_candidate_inventory": [],
            "load_visibility_probe": {
                "full_text_token_hashes": [digest],
                "line_token_hashes": [],
                "layout_word_token_hashes": [],
                "layout_table_token_hashes": [],
            },
        }
        record["artifact_summary"] = {"full_text_present": True}

        result = evaluate_ratecon_against_gold([label], [record])
        recall = result["load_candidate_recall_summary"]

        self.assertEqual(recall["gold_load_not_in_candidates"], 1)
        self.assertEqual(recall["gold_load_visible_in_text_but_not_candidate"], 1)
        self.assertEqual(
            recall["candidate_missing_reason_counts"]["gold_load_visible_in_text_but_not_candidate"],
            1,
        )
        self.assertFalse(recall["documents"][0]["raw_value_printed"])

    def test_load_candidate_recall_counts_ocr_visibility_gap(self):
        label = self._gold_label()
        record = self._audit_record()
        record["private_eval_values"] = {
            "load_identity_candidate_inventory": [],
            "load_visibility_probe": {
                "full_text_token_hashes": [],
                "line_token_hashes": [],
                "layout_word_token_hashes": [],
                "layout_table_token_hashes": [],
            },
        }
        record["triage"] = {"ocr_required": True}
        record["artifact_summary"] = {"full_text_present": False}

        result = evaluate_ratecon_against_gold([label], [record])
        recall = result["load_candidate_recall_summary"]

        self.assertEqual(recall["gold_load_requires_ocr_or_vision"], 1)

    def test_serialized_stop_presence_without_components_is_not_missing(self):
        label = self._gold_label()
        record = self._audit_record()
        record["shadow"]["resolved_fields"]["pickup_stops"] = {
            "value": "pickup_layout_stop_present",
            "confidence": 0.66,
            "structured_stop_summary": {
                "has_location": True,
                "has_date": True,
                "structure_status": "complete",
            },
        }

        result = evaluate_ratecon_against_gold([label], [record])

        shadow_pickup = result["field_metrics"][SYSTEM_SHADOW]["pickup_stops"]
        self.assertEqual(shadow_pickup["missing_count"], 0)
        self.assertEqual(shadow_pickup["field_not_serialized_count"], 1)

    def test_candidate_best_groups_are_evaluated_separately(self):
        label = self._gold_label()
        record = self._audit_record()
        record["private_eval_values"] = {
            "shadow_candidate_best": {
                FIELD_LOAD_NUMBER: {"value": "LOAD-123", "confidence": 0.83}
            },
            "shadow_best_independent_candidate": {
                FIELD_LOAD_NUMBER: {"value": "LOAD-123", "confidence": 0.83}
            },
            "shadow_best_layout_candidate": {
                FIELD_LOAD_NUMBER: {"value": "WRONG", "confidence": 0.84}
            },
        }

        result = evaluate_ratecon_against_gold([label], [record])

        self.assertEqual(
            result["field_metrics"][SYSTEM_SHADOW_CANDIDATE_BEST][FIELD_LOAD_NUMBER][
                "exact_match_count"
            ],
            1,
        )
        self.assertEqual(
            result["field_metrics"][SYSTEM_SHADOW_BEST_INDEPENDENT][FIELD_LOAD_NUMBER][
                "exact_match_count"
            ],
            1,
        )
        self.assertEqual(
            result["field_metrics"][SYSTEM_SHADOW_BEST_LAYOUT][FIELD_LOAD_NUMBER][
                "wrong_value_count"
            ],
            1,
        )

    def test_error_cases_classify_load_and_rate_metadata(self):
        label = self._gold_label()
        record = self._audit_record()
        record["private_eval_values"] = {
            "shadow_selected": {
                FIELD_LOAD_NUMBER: {
                    "value": "PO-999",
                    "confidence": 0.88,
                    "metadata_summary": {"id_type_hint": "po"},
                },
                FIELD_TOTAL_CARRIER_RATE: {
                    "value": "250.00",
                    "confidence": 0.84,
                    "metadata_summary": {"money_context": "accessorial"},
                },
            }
        }

        result = evaluate_ratecon_against_gold([label], [record])

        self.assertEqual(
            result["error_case_breakdown"][FIELD_LOAD_NUMBER][
                "selected_po_reference_instead_of_primary_load"
            ],
            1,
        )
        self.assertEqual(
            result["error_case_breakdown"][FIELD_TOTAL_CARRIER_RATE][
                "selected_accessorial_instead_of_total"
            ],
            1,
        )
        self.assertEqual(
            result["load_number_error_analysis"]["wrong_by_id_type_hint"]["po"],
            1,
        )
        self.assertEqual(
            result["rate_error_analysis"]["wrong_by_money_context"]["accessorial"],
            1,
        )

    def test_table_neighbor_error_summary_classifies_stop_reference_row(self):
        label = self._gold_label()
        record = self._audit_record()
        record["private_eval_values"] = {
            "shadow_selected": {
                FIELD_LOAD_NUMBER: {
                    "value": "WRONG-STOP-REF",
                    "confidence": 0.88,
                    "source": "native_layout",
                    "metadata_summary": {
                        "pairing_method": "table_key_value_row",
                        "table_context_role": "stop_table",
                        "table_row_role": "pickup_delivery_ref_row",
                        "table_neighbor_safety": "unsafe",
                        "table_neighbor_penalty_reason": "pickup_delivery_reference_row",
                        "id_type_hint": "load",
                    },
                },
            }
        }

        result = evaluate_ratecon_against_gold([label], [record])
        summary = result["load_table_neighbor_error_summary"]

        self.assertEqual(summary["wrong_table_neighbor_count"], 1)
        self.assertEqual(
            summary["reason_counts"]["table_neighbor_from_pickup_delivery_ref_row"],
            1,
        )
        self.assertEqual(summary["by_table_neighbor_safety"]["unsafe"], 1)
        self.assertFalse(summary["private_values_printed"])

    def test_remaining_table_neighbor_wrong_summary_classifies_geometry_and_reference(self):
        label = self._gold_label()
        record = self._audit_record()
        record["private_eval_values"] = {
            "shadow_selected": {
                FIELD_LOAD_NUMBER: {
                    "value": "WRONG-STOP-REF",
                    "confidence": 0.88,
                    "source": "native_layout",
                    "metadata_summary": {
                        "pairing_method": "table_key_value_row",
                        "table_context_role": "stop_table",
                        "table_row_role": "pickup_delivery_ref_row",
                        "table_neighbor_safety": "unsafe",
                        "table_neighbor_penalty_reason": "pickup_delivery_reference_row",
                        "id_type_hint": "load",
                    },
                },
            }
        }

        result = evaluate_ratecon_against_gold([label], [record])
        summary = result["remaining_table_neighbor_wrong_summary"]

        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["unknown_count"], 0)
        self.assertEqual(summary["should_be_reference_count"], 1)
        self.assertEqual(
            summary["reason_counts"]["table_neighbor_should_be_reference_not_load"],
            1,
        )

    def test_table_neighbor_value_cell_forensics_uses_safe_counts(self):
        label = self._gold_label()
        record = self._audit_record()
        record["private_eval_values"] = {
            "shadow_selected": {
                FIELD_LOAD_NUMBER: {
                    "value": "WRONG-TABLE-ID",
                    "confidence": 0.88,
                    "source": "native_layout",
                    "parser_name": "layout_load_pairing",
                    "page": 1,
                    "value_shape": {
                        "length": 14,
                        "has_digits": False,
                        "has_letters": True,
                        "looks_like_date": False,
                        "looks_like_money": False,
                        "looks_like_phone": False,
                        "looks_like_address": False,
                    },
                    "metadata_summary": {
                        "pairing_method": "table_key_value_row",
                        "table_context_role": "header_load_info",
                        "table_row_role": "load_id_row",
                        "table_neighbor_safety": "safe",
                        "id_type_hint": "load",
                        "table_index": 1,
                        "row_index": 2,
                        "neighbor_cell_count": 4,
                        "id_like_cell_count_in_row": 2,
                        "load_label_cell_count_in_row": 1,
                        "reference_label_cell_count_in_row": 1,
                    },
                },
            },
        }

        result = evaluate_ratecon_against_gold([label], [record])
        summary = result["load_table_neighbor_value_cell_forensics"]

        self.assertEqual(summary["wrong_table_neighbor_count"], 1)
        self.assertEqual(summary["diagnosis_counts"]["ambiguous_multi_id_row"], 1)
        case = summary["cases"][0]
        self.assertEqual(case["selected_candidate"]["neighbor_cell_count"], 4)
        self.assertEqual(case["selected_candidate"]["id_like_cell_count_in_row"], 2)
        self.assertNotIn("WRONG-TABLE-ID", json.dumps(summary))
        self.assertFalse(summary["private_values_printed"])

    def test_table_neighbor_abstention_summary_counts_private_eval_candidates(self):
        label = self._gold_label()
        record = self._audit_record()
        record["private_eval_values"] = {
            "load_identity_candidate_inventory": [
                {
                    "field": "reference_numbers",
                    "value": "ABSTAINED-ID",
                    "confidence": 0.35,
                    "source": "native_layout",
                    "metadata_summary": {
                        "pairing_method": "table_key_value_row",
                        "table_neighbor_abstained": True,
                        "table_neighbor_demoted_from_load_number": True,
                        "table_neighbor_abstention_reason": (
                            "table_neighbor_multi_id_unclear_alignment"
                        ),
                        "selection_policy": "abstain",
                    },
                },
            ],
            "shadow_selected": {
                FIELD_LOAD_NUMBER: {
                    "value": "",
                    "confidence": 0.0,
                    "source_status": "extractor_missing",
                },
            },
        }

        result = evaluate_ratecon_against_gold([label], [record])
        summary = result["table_neighbor_abstention_summary"]

        self.assertEqual(summary["abstained_candidate_count"], 1)
        self.assertEqual(summary["demoted_from_load_number_count"], 1)
        self.assertEqual(
            summary["reason_counts"]["table_neighbor_multi_id_unclear_alignment"],
            1,
        )
        self.assertEqual(summary["selection_policy_counts"]["abstain"], 1)
        self.assertEqual(summary["by_system"]["load_identity_candidate_inventory"], 1)
        self.assertNotIn("ABSTAINED-ID", json.dumps(summary))

    def test_ocr_vision_backlog_counts_low_text_without_running_ocr(self):
        label = self._gold_label()
        record = self._audit_record()
        record["triage"] = {
            "ocr_required": True,
            "pdf_type": "scanned",
            "page_count": 2,
            "native_text_token_count": 0,
        }
        record["artifact_summary"] = {
            "full_text_present": False,
            "word_count": 0,
            "table_count": 0,
            "layout_provider_summary": {"status": "partial"},
        }

        result = evaluate_ratecon_against_gold([label], [record])
        backlog = result["ocr_vision_backlog_summary"]

        self.assertEqual(backlog["ocr_or_vision_required_doc_count"], 1)
        self.assertEqual(backlog["overall_docs"], 1)
        self.assertEqual(backlog["evaluated_rc_docs"], 1)
        self.assertEqual(backlog["skipped_non_rc_docs"], 0)
        self.assertEqual(backlog["load_blocked_docs"], 1)
        self.assertEqual(backlog["rate_blocked_docs"], 1)
        self.assertEqual(backlog["stop_blocked_docs"], 1)
        self.assertEqual(backlog["recommended_next_route_counts"]["ocr"], 1)
        self.assertEqual(backlog["pdf_type_counts"]["scanned"], 1)
        self.assertFalse(backlog["ocr_run"])
        self.assertFalse(backlog["ai_cloud_used"])

    def test_ocr_vision_backlog_separates_skipped_non_ratecon(self):
        skipped = self._gold_label()
        skipped["document_id"] = "DOC-29"
        skipped["file_name"] = "LoadConfirmation29.pdf"
        skipped["label_status"] = LABEL_SKIPPED
        skipped["skip_reason"] = "not_rate_confirmation"
        record = self._audit_record()
        record["document_id"] = "RATECON_029"
        record["file_name"] = "LoadConfirmation29.pdf"
        record["triage"] = {
            "ocr_required": False,
            "pdf_type": "low_text",
            "page_count": 1,
            "native_text_token_count": 2,
        }
        record["artifact_summary"] = {
            "full_text_present": False,
            "word_count": 0,
            "table_count": 0,
            "layout_provider_summary": {"status": "partial"},
        }

        result = evaluate_ratecon_against_gold([skipped], [record])
        backlog = result["ocr_vision_backlog_summary"]

        self.assertEqual(backlog["overall_docs"], 1)
        self.assertEqual(backlog["evaluated_rc_docs"], 0)
        self.assertEqual(backlog["skipped_non_rc_docs"], 1)
        self.assertEqual(
            backlog["recommended_next_route_counts"]["document_classification"],
            1,
        )

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

    def test_evaluator_merges_private_eval_values_from_legacy_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            gold_dir = Path(tmp) / "gold"
            gold_dir.mkdir()
            (gold_dir / "doc1.json").write_text(
                json.dumps(self._gold_label()),
                encoding="utf-8",
            )
            audit = Path(tmp) / "audit.jsonl"
            base_record = self._audit_record()
            base_record["legacy"] = {
                "load_number": "",
                "fields_present": ["load_number"],
                "pickup_count": 0,
                "delivery_count": 0,
            }
            audit.write_text(json.dumps(base_record) + "\n", encoding="utf-8")

            legacy_dir = Path(tmp) / "legacy_output"
            legacy_dir.mkdir()
            sidecar_record = dict(base_record)
            sidecar_record["private_eval_values"] = {
                "legacy_selected": {
                    FIELD_LOAD_NUMBER: {"value": "LOAD-123", "confidence": None}
                }
            }
            (legacy_dir / "ratecon_shadow_document_pipeline_audit.jsonl").write_text(
                json.dumps(sidecar_record) + "\n",
                encoding="utf-8",
            )
            output = Path(tmp) / "eval"

            evaluate_and_write(
                gold_path=gold_dir,
                audit_path=audit,
                legacy_output_dir=legacy_dir,
                output_dir=output,
                allow_custom_output_dir=True,
            )
            summary = json.loads(
                (output / "ratecon_gold_evaluation_summary.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertTrue(summary["legacy_source"]["explicit_legacy_source_loaded"])
            self.assertEqual(
                summary["field_metrics"][SYSTEM_LEGACY][FIELD_LOAD_NUMBER][
                    "exact_match_count"
                ],
                1,
            )

    def test_compare_gold_evaluation_summaries_reports_deltas(self):
        baseline = {
            "labels_evaluated": 1,
            "field_metrics": {
                SYSTEM_SHADOW: {
                    FIELD_LOAD_NUMBER: {
                        "exact_match_count": 0,
                        "normalized_match_count": 0,
                        "missing_count": 1,
                        "wrong_value_count": 0,
                        "precision": 0.0,
                        "recall": 0.0,
                        "high_confidence_but_wrong_count": 0,
                    },
                    FIELD_TOTAL_CARRIER_RATE: {
                        "exact_match_count": 0,
                        "normalized_match_count": 1,
                        "missing_count": 0,
                        "wrong_value_count": 1,
                        "precision": 0.5,
                        "recall": 0.5,
                        "high_confidence_but_wrong_count": 1,
                    }
                }
            },
            "load_number_error_analysis": {
                "wrong_selected_count": 0,
                "missing_count": 1,
            },
            "rate_error_analysis": {
                "wrong_selected_count": 1,
                "missing_count": 0,
                "gold_total_in_candidates_not_selected": 1,
            },
            "load_candidate_recall_summary": {
                "evaluated_docs": 1,
                "gold_load_in_any_candidate": 0,
                "gold_load_in_independent_candidate": 0,
                "gold_load_in_layout_candidate": 0,
                "gold_load_in_header_candidate": 0,
                "gold_load_in_table_candidate": 0,
                "gold_load_in_legacy_fallback_candidate": 0,
                "gold_load_not_in_candidates": 1,
                "gold_load_visible_in_text_but_not_candidate": 1,
                "gold_load_visible_in_layout_but_not_candidate": 0,
                "gold_load_requires_ocr_or_vision": 0,
            },
        }
        experiment = {
            "labels_evaluated": 1,
            "field_metrics": {
                SYSTEM_SHADOW: {
                    FIELD_LOAD_NUMBER: {
                        "exact_match_count": 1,
                        "normalized_match_count": 0,
                        "missing_count": 0,
                        "wrong_value_count": 0,
                        "precision": 1.0,
                        "recall": 1.0,
                        "high_confidence_but_wrong_count": 0,
                    },
                    FIELD_TOTAL_CARRIER_RATE: {
                        "exact_match_count": 0,
                        "normalized_match_count": 2,
                        "missing_count": 0,
                        "wrong_value_count": 0,
                        "precision": 1.0,
                        "recall": 1.0,
                        "high_confidence_but_wrong_count": 0,
                    }
                }
            },
            "load_number_error_analysis": {
                "wrong_selected_count": 0,
                "missing_count": 0,
            },
            "rate_error_analysis": {
                "wrong_selected_count": 0,
                "missing_count": 0,
                "gold_total_in_candidates_not_selected": 0,
            },
            "load_candidate_recall_summary": {
                "evaluated_docs": 1,
                "gold_load_in_any_candidate": 1,
                "gold_load_in_independent_candidate": 1,
                "gold_load_in_layout_candidate": 1,
                "gold_load_in_header_candidate": 1,
                "gold_load_in_table_candidate": 0,
                "gold_load_in_legacy_fallback_candidate": 0,
                "gold_load_not_in_candidates": 0,
                "gold_load_visible_in_text_but_not_candidate": 0,
                "gold_load_visible_in_layout_but_not_candidate": 0,
                "gold_load_requires_ocr_or_vision": 0,
            },
        }

        comparison = compare_summaries(baseline, experiment)

        self.assertEqual(
            comparison["shadow_field_deltas"][FIELD_LOAD_NUMBER]["delta"]["correct_count"],
            1,
        )
        self.assertEqual(
            comparison["load_number_error_analysis_delta"]["delta"]["missing_count"],
            -1,
        )
        self.assertEqual(
            comparison["load_candidate_recall_delta"]["delta"]["gold_load_in_any_candidate"],
            1,
        )
        self.assertEqual(
            comparison["rate_profile_safety_summary"]["correct_delta"],
            1,
        )
        self.assertEqual(
            comparison["rate_profile_safety_summary"]["wrong_delta"],
            -1,
        )

    def test_compare_profiles_reports_all_configurations(self):
        def summary(load_correct, load_wrong, rate_correct, table_wrong):
            return {
                "labels_evaluated": 31,
                "field_metrics": {
                    SYSTEM_SHADOW: {
                        FIELD_LOAD_NUMBER: {
                            "exact_match_count": load_correct,
                            "normalized_match_count": 0,
                            "missing_count": 31 - load_correct - load_wrong,
                            "wrong_value_count": load_wrong,
                            "precision": round(load_correct / max(load_correct + load_wrong, 1), 4),
                            "recall": round(load_correct / 31, 4),
                            "high_confidence_but_wrong_count": 2,
                        },
                        FIELD_TOTAL_CARRIER_RATE: {
                            "exact_match_count": rate_correct,
                            "normalized_match_count": 0,
                            "missing_count": 31 - rate_correct,
                            "wrong_value_count": 0,
                            "precision": 1.0,
                            "recall": round(rate_correct / 31, 4),
                            "high_confidence_but_wrong_count": 0,
                        },
                    }
                },
                "load_number_error_analysis": {
                    "wrong_reason_counts": {
                        "selected_table_neighbor_wrong_cell": table_wrong,
                    }
                },
                "load_candidate_recall_summary": {
                    "gold_load_in_any_candidate": load_correct + 1,
                    "gold_load_not_in_candidates": 31 - load_correct - 1,
                },
                "load_table_neighbor_error_summary": {
                    "wrong_table_neighbor_count": table_wrong,
                    "reason_counts": {"table_neighbor_from_stop_reference_row": table_wrong},
                },
                "table_neighbor_abstention_summary": {
                    "abstained_candidate_count": table_wrong,
                    "reason_counts": {"table_neighbor_multi_id_unclear_alignment": table_wrong},
                },
                "rate_error_analysis": {"wrong_reason_counts": {}},
            }

        comparison = compare_profiles(
            {
                "baseline": summary(9, 10, 13, 6),
                "header_recall_v1": summary(15, 7, 13, 6),
                "header_recall_table_safety_v1": summary(15, 5, 13, 4),
                "combined": summary(15, 5, 15, 4),
            }
        )

        self.assertEqual(len(comparison["profiles"]), 4)
        self.assertEqual(
            comparison["profiles"]["header_recall_table_safety_v1"]["load_number"][
                "selected_table_neighbor_wrong_cell"
            ],
            4,
        )
        self.assertEqual(
            comparison["deltas_from_first_profile"]["combined"]["total_carrier_rate"][
                "correct_count"
            ],
            2,
        )
        self.assertEqual(
            comparison["deltas_from_first_profile"]["combined"][
                "table_neighbor_abstention"
            ]["abstained_candidate_count"],
            -2,
        )


if __name__ == "__main__":
    unittest.main()
