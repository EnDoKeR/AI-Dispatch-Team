import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.field_candidate_resolver import resolve_candidates
from app.document_ai.ratecon_gold_labels import (
    FIELD_DELIVERY_STOPS,
    FIELD_PICKUP_STOPS,
    SYSTEM_SHADOW,
    SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP,
    SYSTEM_SHADOW_BEST_OCR_COLUMN_STOP,
    SYSTEM_SHADOW_STOP_REVIEW_DRAFT,
    build_stop_gold_completeness_summary,
    evaluate_ratecon_against_gold,
)
from app.document_ai.ratecon_shadow_audit import build_private_eval_values
from app.document_ai.ratecon_stop_component_policy import (
    STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
    apply_stop_column_strict_profile_to_candidates,
)
from app.document_ai.ratecon_stop_draft_profile import (
    STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
    STOP_DRAFT_PROFILE_NONE,
)
from scripts.create_ratecon_stop_gold_review_packets import (
    build_no_candidate_source_trace_summary,
    build_residual_extraction_report,
    build_patch_template,
    build_stop_gold_review_packet,
    build_stop_source_inventory_report,
    write_residual_extraction_report,
    write_stop_source_inventory_report,
    write_packet,
)
from scripts.apply_ratecon_stop_gold_review_patch import (
    _require_safe_path,
    plan_stop_gold_patch,
)


def _dispatch_candidate():
    return {
        "field": FIELD_PICKUP_STOPS,
        "value": [
            {
                "role": "pickup",
                "stop_index": 1,
                "city": "Dallas",
                "state": "TX",
                "date": "06/05/2026",
                "appointment_window": "0700 to 1500",
            }
        ],
        "confidence": 0.82,
        "source": "ocr",
        "parser_name": "ocr_stop_table_reconstructor",
        "metadata": {
            "candidate_id": "pickup-column-1",
            "structured_stop_candidate": True,
            "dispatch_usable": True,
            "assembled_from_column_geometry": True,
            "pairing_method": "ocr_geometry_column_row",
            "stop_role": "pickup",
            "has_location": True,
            "has_date": True,
            "has_time": True,
            "has_facility": False,
            "has_address": False,
            "row_boundary_confidence": 0.75,
            "column_alignment_confidence": 0.75,
            "stop_column_status": "medium",
            "stop_column_warnings": [],
        },
    }


def _placeholder_stop_candidate(candidate_id="placeholder-pickup", stop_abstained=False):
    return {
        "field": FIELD_PICKUP_STOPS,
        "value": "pickup_stop_complete",
        "confidence": 0.4,
        "source": "ocr",
        "parser_name": "ocr_stop_table_reconstructor",
        "metadata": {
            "candidate_id": candidate_id,
            "structured_stop_candidate": True,
            "assembled_from_column_geometry": True,
            "pairing_method": "ocr_geometry_column_row",
            "stop_role": "pickup",
            "stop_index": 1,
            "has_location": not stop_abstained,
            "has_date": False,
            "has_time": False,
            "stop_abstained": stop_abstained,
            "stop_selection_policy": "abstain" if stop_abstained else "partial_review",
            "stop_abstention_reason": "no_location_or_date" if stop_abstained else "location_only_review",
        },
    }


def _unparsed_location_stop_candidate():
    return {
        "field": FIELD_PICKUP_STOPS,
        "value": "Warehouse District",
        "confidence": 0.45,
        "source": "native_text",
        "parser_name": "stop_evidence_assembler",
        "metadata": {
            "structured_stop_candidate": True,
            "stop_role": "pickup",
            "stop_index": 1,
            "has_location": True,
            "has_date": False,
            "has_time": False,
            "stop_selection_policy": "partial_review",
        },
    }


def _gold_label():
    return {
        "document_id": "DOC-HANDOFF",
        "file_hash": "hash-handoff",
        "file_name": "handoff.pdf",
        "label_status": "labeled",
        "gold": {
            "pickup_stops": [
                {
                    "city": "Dallas",
                    "state": "TX",
                    "date": "2026-06-05",
                    "appointment_window": "07:00-15:00",
                }
            ]
        },
    }


def _incomplete_gold_label():
    label = _gold_label()
    label["gold"] = {
        "pickup_stops": [
            {
                "date": "2026-06-05",
                "appointment_window": "07:00-15:00",
            }
        ]
    }
    return label


def _known_absent_city_level_gold_label():
    label = _gold_label()
    label["gold"] = {
        "pickup_stops": [
            {
                "city": "Dallas",
                "state": "TX",
                "date": "2026-06-05",
                "time": None,
                "appointment_window": None,
                "uncertain": True,
                "notes": "Only origin city/state shown; no shipper/address in document",
            }
        ]
    }
    label["labeler"] = {
        "review_notes": "Only city-level stops visible in source document",
    }
    return label


def _visible_time_missing_gold_label():
    label = _known_absent_city_level_gold_label()
    label["gold"]["pickup_stops"][0]["notes"] = (
        "Appointment time visible in source but missing from gold"
    )
    label["labeler"] = {"review_notes": "Document shows time/window value"}
    return label


def _optional_location_missing_gold_label():
    label = _gold_label()
    label["gold"] = {
        "pickup_stops": [
            {
                "facility": None,
                "address": None,
                "city": "Dallas",
                "state": "TX",
                "zip": None,
                "date": "2026-06-05",
                "appointment_window": "0700 to 1500",
                "uncertain": True,
                "notes": "Only origin city/state shown; no shipper/address in document",
            }
        ]
    }
    return label


def _audit_record(candidates, resolved, stop_draft_profile=STOP_DRAFT_PROFILE_NONE):
    return {
        "document_id": "DOC-HANDOFF",
        "file_hash": "hash-handoff",
        "file_name": "handoff.pdf",
        "shadow": {
            "resolved_fields": resolved.get("resolved_fields", {}),
            "resolver_decision_traces": resolved.get("resolver_decision_traces", {}),
        },
        "legacy": {},
        "private_eval_values": build_private_eval_values(
            raw_resolved=resolved.get("resolved_fields", {}),
            candidates=candidates,
            stop_draft_profile=stop_draft_profile,
        ),
    }


def _source_inventory_audit_record():
    return {
        "document_id": "DOC-HANDOFF",
        "file_hash": "hash-handoff",
        "file_name": "handoff.pdf",
        "candidate_counts_by_field": {
            FIELD_PICKUP_STOPS: 1,
            "delivery_location": 1,
            "delivery_time": 1,
        },
        "private_eval_values": {
            "stop_component_candidate_inventory": [
                {
                    "candidate_id": "pickup-native-1",
                    "field": FIELD_PICKUP_STOPS,
                    "value": [
                        {
                            "role": "pickup",
                            "stop_index": 1,
                            "city": "Dallas",
                            "state": "TX",
                            "date": "2026-06-05",
                        }
                    ],
                    "source": "native_text",
                    "parser_name": "stop_evidence_assembler",
                    "metadata_summary": {
                        "candidate_id": "pickup-native-1",
                        "stop_role": "pickup",
                        "page": 1,
                        "line_index": 4,
                    },
                },
                {
                    "candidate_id": "delivery-ocr-1",
                    "field": FIELD_DELIVERY_STOPS,
                    "value": [
                        {
                            "role": "delivery",
                            "stop_index": 1,
                            "city": "Austin",
                            "state": "TX",
                            "appointment_window": "0800 to 1000",
                        }
                    ],
                    "source": "ocr",
                    "parser_name": "ocr_stop_table_reconstructor",
                    "metadata_summary": {
                        "candidate_id": "delivery-ocr-1",
                        "stop_role": "delivery",
                        "assembled_from_column_geometry": True,
                        "component_bboxes_available": True,
                        "page": 1,
                        "line_index": 8,
                    },
                },
            ]
        },
    }


class RateConStopDispatchHandoffTests(unittest.TestCase):
    def test_dispatch_candidate_handoff_and_candidate_best_groups(self):
        candidates = apply_stop_column_strict_profile_to_candidates([_dispatch_candidate()])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )
        audit = _audit_record(
            candidates,
            resolved,
            stop_draft_profile=STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
        )

        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        handoff = evaluation["dispatch_usable_handoff_summary"]
        groups = evaluation["stop_candidate_group_metrics"]
        drafts = evaluation["stop_draft_profile_metrics"]

        self.assertEqual(handoff["dispatch_usable_candidates"], 1)
        self.assertEqual(handoff["kept_after_dedupe"], 1)
        self.assertEqual(handoff["resolver_eligible"], 1)
        self.assertEqual(handoff["serialized_for_eval"], 1)
        self.assertIn("evaluator_usability_tier_counts", handoff)
        self.assertEqual(handoff["serialized_gap_count"], 0)
        self.assertGreater(
            groups[SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP]["pickup"]["dispatch_usable"]
            + groups[SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP]["pickup"]["exact_complete"],
            0,
        )
        self.assertGreater(
            groups[SYSTEM_SHADOW_BEST_OCR_COLUMN_STOP]["pickup"]["dispatch_usable"]
            + groups[SYSTEM_SHADOW_BEST_OCR_COLUMN_STOP]["pickup"]["exact_complete"],
            0,
        )
        self.assertGreater(
            drafts[SYSTEM_SHADOW_STOP_REVIEW_DRAFT]["pickup"]["dispatch_usable"]
            + drafts[SYSTEM_SHADOW_STOP_REVIEW_DRAFT]["pickup"]["exact_complete"],
            0,
        )

    def test_draft_profile_default_none_and_explicit_review_draft(self):
        candidates = apply_stop_column_strict_profile_to_candidates([_dispatch_candidate()])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )

        default_payload = build_private_eval_values(
            raw_resolved=resolved.get("resolved_fields", {}),
            candidates=candidates,
            stop_draft_profile=STOP_DRAFT_PROFILE_NONE,
        )
        explicit_payload = build_private_eval_values(
            raw_resolved=resolved.get("resolved_fields", {}),
            candidates=candidates,
            stop_draft_profile=STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
        )

        self.assertEqual(default_payload["shadow_stop_review_draft"], {})
        self.assertIn(FIELD_PICKUP_STOPS, explicit_payload["shadow_stop_review_draft"])
        self.assertTrue(explicit_payload["shadow_stop_review_draft"][FIELD_PICKUP_STOPS]["review_required"])

    def test_selected_structured_stop_components_serialize_in_private_eval(self):
        candidates = apply_stop_column_strict_profile_to_candidates([_dispatch_candidate()])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )
        payload = build_private_eval_values(
            raw_resolved=resolved.get("resolved_fields", {}),
            candidates=candidates,
            stop_draft_profile=STOP_DRAFT_PROFILE_NONE,
        )
        selected = payload["shadow_selected_stop"][FIELD_PICKUP_STOPS]

        self.assertTrue(selected["component_values_serialized"])
        self.assertIsInstance(selected["value"], list)
        self.assertEqual(selected["value"][0]["city"], "Dallas")
        self.assertNotEqual(selected.get("source_status"), "shadow_component_not_serialized")

    def test_abstained_selected_stop_placeholder_is_missing_not_serialized_gap(self):
        candidate = _placeholder_stop_candidate(stop_abstained=True)
        resolved = {
            "resolved_fields": {
                FIELD_PICKUP_STOPS: {
                    "selected_candidate": candidate,
                    "confidence": 0.4,
                }
            }
        }
        audit = _audit_record([candidate], resolved)

        selected = audit["private_eval_values"]["shadow_selected_stop"][FIELD_PICKUP_STOPS]
        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        shadow_row = next(
            row
            for row in evaluation["comparison_rows"]
            if row["system"] == SYSTEM_SHADOW and row["field"] == FIELD_PICKUP_STOPS
        )

        self.assertEqual(selected["source_status"], "shadow_extractor_missing")
        self.assertEqual(selected["serialization_gap_reason"], "selected_stop_really_missing")
        self.assertEqual(shadow_row["dispatch_usability_tier"], "missing_review_required")
        self.assertEqual(evaluation["selected_stop_serialization_gap_summary"]["total"], 0)

    def test_candidate_id_mismatch_is_not_joined_to_wrong_structured_candidate(self):
        selected_candidate = _placeholder_stop_candidate(candidate_id="selected-other")
        structured_candidate = _dispatch_candidate()
        structured_candidate["source"] = selected_candidate["source"]
        structured_candidate["parser_name"] = selected_candidate["parser_name"]
        resolved = {
            "resolved_fields": {
                FIELD_PICKUP_STOPS: {
                    "selected_candidate": selected_candidate,
                    "confidence": 0.4,
                }
            }
        }
        audit = _audit_record([structured_candidate], resolved)
        selected = audit["private_eval_values"]["shadow_selected_stop"][FIELD_PICKUP_STOPS]
        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])

        self.assertFalse(selected["component_values_serialized"])
        self.assertEqual(selected["source_status"], "selected_partial_not_comparable")
        self.assertEqual(
            selected["serialization_gap_reason"],
            "selected_value_has_placeholder_only_no_component",
        )
        self.assertEqual(
            evaluation["selected_stop_serialization_gap_summary"]["total"],
            0,
        )
        self.assertEqual(
            evaluation["remaining_sidecar_component_gap_summary"]["reason_counts"],
            {"selected_value_has_placeholder_only_no_component": 1},
        )

    def test_unparsed_location_only_partial_serializes_local_only_text(self):
        candidate = _unparsed_location_stop_candidate()
        resolved = {
            "resolved_fields": {
                FIELD_PICKUP_STOPS: {
                    "value": candidate["value"],
                    "confidence": candidate["confidence"],
                    "source": candidate["source"],
                    "parser_name": candidate["parser_name"],
                    "metadata": candidate["metadata"],
                }
            }
        }
        audit = _audit_record([candidate], resolved)
        selected = audit["private_eval_values"]["shadow_selected_stop"][FIELD_PICKUP_STOPS]
        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        row = next(
            row
            for row in evaluation["comparison_rows"]
            if row["system"] == SYSTEM_SHADOW and row["field"] == FIELD_PICKUP_STOPS
        )

        self.assertTrue(selected["component_values_serialized"])
        self.assertEqual(selected["source_status"], "unsupported_unparsed_location")
        self.assertEqual(selected["value"][0]["unparsed_location_text_local_only"], "Warehouse District")
        self.assertEqual(row["status"], "unsupported_unparsed_location")
        self.assertEqual(row["dispatch_usability_tier"], "unsupported_unparsed_location")

    def test_stop_gold_review_packet_is_local_only_and_does_not_modify_gold(self):
        candidates = apply_stop_column_strict_profile_to_candidates([_dispatch_candidate()])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )
        audit = _audit_record(
            candidates,
            resolved,
            stop_draft_profile=STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
        )
        gold = [_gold_label()]

        packet = build_stop_gold_review_packet(
            gold,
            [audit],
            include_private_values_local_only=True,
        )

        self.assertFalse(packet["gold_labels_modified"])
        self.assertTrue(packet["local_only"])
        self.assertTrue(packet["private_values_printed"])
        self.assertIn("stop_gold_completeness_summary", packet)
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_packet(packet, Path(tmpdir))
            self.assertTrue(Path(paths["items_json"]).exists())
            self.assertTrue(Path(paths["summary_md"]).exists())
            self.assertTrue(Path(paths["items_csv"]).exists())
            self.assertTrue(Path(paths["code_issues_csv"]).exists())
            self.assertTrue(Path(paths["manual_review_items_csv"]).exists())
            self.assertTrue(Path(paths["patch_template_json"]).exists())
            self.assertTrue(Path(paths["selected_stop_serialization_gaps_csv"]).exists())
            self.assertTrue(Path(paths["selected_stop_serialization_gaps_json"]).exists())
            self.assertTrue(Path(paths["selected_stop_component_side_by_side_csv"]).exists())

    def test_patch_template_only_includes_true_gold_review_rows(self):
        candidates = apply_stop_column_strict_profile_to_candidates([_dispatch_candidate()])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )
        audit = _audit_record(
            candidates,
            resolved,
            stop_draft_profile=STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
        )

        complete_packet = build_stop_gold_review_packet([_gold_label()], [audit])
        incomplete_packet = build_stop_gold_review_packet([_incomplete_gold_label()], [audit])

        self.assertEqual(build_patch_template(complete_packet)["patches"], [])
        self.assertEqual(len(build_patch_template(incomplete_packet)["patches"]), 1)
        proposed = build_patch_template(incomplete_packet)["patches"][0]["proposed_gold"]
        self.assertTrue(all(value is None for value in proposed.values()))

    def test_known_absent_city_level_missing_time_is_no_action(self):
        packet = build_stop_gold_review_packet(
            [_known_absent_city_level_gold_label()],
            [],
        )

        self.assertEqual(packet["category_counts"]["true_gold_review_needed"], 0)
        self.assertEqual(packet["category_counts"]["no_action_needed"], 1)
        self.assertEqual(packet["known_absent_summary"]["known_absent_items"], 1)
        self.assertEqual(packet["items"][0]["suspect_reason"], "gold_time_window_not_visible_in_source")
        self.assertEqual(build_patch_template(packet)["patches"], [])

    def test_visible_missing_time_remains_true_gold_review(self):
        packet = build_stop_gold_review_packet(
            [_visible_time_missing_gold_label()],
            [],
        )

        self.assertEqual(packet["category_counts"]["true_gold_review_needed"], 1)
        self.assertEqual(packet["known_absent_summary"]["known_absent_items"], 0)
        self.assertEqual(len(build_patch_template(packet)["patches"]), 1)

    def test_missing_optional_location_details_do_not_trigger_gold_review(self):
        packet = build_stop_gold_review_packet(
            [_optional_location_missing_gold_label()],
            [],
        )

        self.assertEqual(packet["category_counts"]["true_gold_review_needed"], 0)
        self.assertEqual(build_patch_template(packet)["patches"], [])

    def test_known_absent_csv_generated_and_manual_review_empty(self):
        packet = build_stop_gold_review_packet(
            [_known_absent_city_level_gold_label()],
            [],
            include_private_values_local_only=True,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_packet(packet, Path(tmpdir))
            known_absent_path = Path(paths["known_absent_items_csv"])
            manual_path = Path(paths["manual_review_items_csv"])

            self.assertTrue(known_absent_path.exists())
            self.assertIn("gold_time_window_not_visible_in_source", known_absent_path.read_text())
            self.assertEqual(len(manual_path.read_text().strip().splitlines()), 1)

    def test_exclusive_category_counts_are_mutually_exclusive(self):
        packet = build_stop_gold_review_packet(
            [_known_absent_city_level_gold_label()],
            [],
        )

        exclusive = packet["exclusive_category_counts"]
        self.assertEqual(exclusive["known_absent_no_action"], 1)
        self.assertEqual(exclusive["total_unique_items"], 1)
        self.assertIn("mutually exclusive", exclusive["notes"])
        self.assertEqual(build_patch_template(packet)["patches"], [])

    def test_residual_extraction_report_classifies_location_only_partial(self):
        packet = {
            "exclusive_category_counts": {
                "extraction_candidate_issue": 1,
                "total_unique_items": 1,
            },
            "private_values_printed": True,
            "items": [
                {
                    "document_id": "DOC-HANDOFF",
                    "file_hash": "hash-handoff",
                    "file_name": "handoff.pdf",
                    "field": FIELD_PICKUP_STOPS,
                    "categories": ["extraction_candidate_issue"],
                    "selected_stop_component_summary": {
                        "raw_status": "partial_match",
                        "dispatch_usability_tier": "useful_partial_location_only",
                        "has_location": True,
                        "has_date": False,
                        "has_time": False,
                    },
                    "selected_components": {"city": "Dallas", "state": "TX"},
                    "selected_source_hint": {
                        "source": "native_text",
                        "parser_name": "stop_evidence_assembler",
                    },
                    "best_candidate_components": {},
                    "draft_components": {},
                    "gold_components": {"city": "Dallas", "state": "TX", "date": "2026-06-05"},
                }
            ],
        }

        report = build_residual_extraction_report(packet)

        self.assertEqual(report["residual_item_count"], 1)
        self.assertEqual(report["candidate_issue_type_counts"]["selected_location_only_partial"], 1)
        self.assertEqual(report["recommended_fix_type_counts"]["candidate_fusion"], 1)
        self.assertEqual(report["stop_component_fusion_opportunity_summary"]["fusion_not_possible"], 1)
        self.assertEqual(report["stop_residual_decision"]["pickup"], "needs_component_fusion")

    def test_residual_extraction_report_detects_fusion_opportunity(self):
        packet = {
            "exclusive_category_counts": {},
            "items": [
                {
                    "document_id": "DOC-HANDOFF",
                    "file_hash": "hash-handoff",
                    "file_name": "handoff.pdf",
                    "field": FIELD_PICKUP_STOPS,
                    "categories": ["extraction_candidate_issue"],
                    "selected_stop_component_summary": {
                        "raw_status": "partial_match",
                        "dispatch_usability_tier": "useful_partial_location_only",
                        "has_location": True,
                    },
                    "selected_components": {"city": "Dallas", "state": "TX"},
                    "best_candidate_components": {
                        "date": "2026-06-05",
                        "appointment_window": "0700 to 1500",
                    },
                    "best_candidate_source_hint": {
                        "source": "ocr",
                        "parser_name": "ocr_stop_table_reconstructor",
                    },
                    "draft_components": {},
                    "gold_components": {},
                }
            ],
        }

        report = build_residual_extraction_report(packet)
        summary = report["stop_component_fusion_opportunity_summary"]

        self.assertEqual(summary["fusion_possible"], 1)
        self.assertEqual(summary["same_role_location_date_available"], 1)
        self.assertEqual(summary["same_role_location_time_available"], 1)

    def test_residual_extraction_report_blocks_wrong_role_and_payment_fusion(self):
        packet = {
            "exclusive_category_counts": {},
            "items": [
                {
                    "document_id": "DOC-HANDOFF",
                    "file_hash": "hash-handoff",
                    "file_name": "handoff.pdf",
                    "field": FIELD_PICKUP_STOPS,
                    "categories": ["extraction_candidate_issue"],
                    "selected_stop_component_summary": {
                        "raw_status": "wrong",
                        "dispatch_usability_tier": "unsafe_wrong",
                        "has_location": True,
                        "has_date": True,
                        "issues": ["wrong_role", "component_from_payment_section"],
                    },
                    "selected_components": {"city": "Dallas", "state": "TX", "date": "2026-06-05"},
                    "selected_source_hint": {"source": "ocr"},
                    "best_candidate_components": {},
                    "draft_components": {},
                    "gold_components": {},
                }
            ],
        }

        report = build_residual_extraction_report(packet)
        blocked = report["stop_component_fusion_opportunity_summary"]["blocked_reason_counts"]

        self.assertEqual(report["stop_component_fusion_opportunity_summary"]["fusion_possible"], 0)
        self.assertEqual(blocked["component_from_wrong_role"], 1)
        self.assertEqual(blocked["component_from_payment_or_instruction"], 1)

    def test_residual_extraction_report_writer_is_local_only(self):
        packet = {
            "exclusive_category_counts": {},
            "private_values_printed": True,
            "items": [
                {
                    "document_id": "DOC-HANDOFF",
                    "file_hash": "hash-handoff",
                    "file_name": "handoff.pdf",
                    "field": FIELD_PICKUP_STOPS,
                    "categories": ["extraction_candidate_issue"],
                    "selected_stop_component_summary": {"has_location": True},
                    "selected_components": {"city": "Dallas"},
                    "selected_source_hint": {"source": "native_text"},
                    "best_candidate_components": {},
                    "draft_components": {},
                    "gold_components": {"city": "Dallas"},
                }
            ],
        }
        report = build_residual_extraction_report(packet)
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_residual_extraction_report(report, Path(tmpdir))

            self.assertTrue(Path(paths["summary_md"]).exists())
            self.assertTrue(Path(paths["items_csv"]).exists())
            self.assertTrue(Path(paths["items_json"]).exists())

    def test_stop_source_inventory_exports_components_and_redacts_by_default(self):
        report = build_stop_source_inventory_report(
            {},
            [_source_inventory_audit_record()],
            include_private_values=False,
        )

        self.assertEqual(report["source_inventory_summary"]["inventory_item_count"], 4)
        self.assertEqual(report["source_inventory_summary"]["by_source"]["ocr_geometry_column"], 2)
        self.assertEqual(report["source_inventory_summary"]["by_source"]["stop_evidence_assembler"], 2)
        self.assertTrue(all(item["value_local_only"] == "" for item in report["items"]))
        doc = next(iter(report["stop_component_availability_matrix"].values()))
        self.assertTrue(doc["pickup"]["has_same_role_location_date"])
        self.assertTrue(doc["delivery"]["has_same_role_location_time"])

    def test_stop_source_inventory_includes_private_values_only_with_flag(self):
        redacted = build_stop_source_inventory_report(
            {},
            [_source_inventory_audit_record()],
            include_private_values=False,
        )
        private = build_stop_source_inventory_report(
            {},
            [_source_inventory_audit_record()],
            include_private_values=True,
        )

        self.assertFalse(any(item["value_local_only"] for item in redacted["items"]))
        self.assertTrue(any(item["value_local_only"] == "Dallas TX" for item in private["items"]))

    def test_stop_source_inventory_writer_outputs_local_files(self):
        report = build_stop_source_inventory_report(
            {},
            [_source_inventory_audit_record()],
            include_private_values=True,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_stop_source_inventory_report(report, Path(tmpdir))

            self.assertTrue(Path(paths["summary_md"]).exists())
            self.assertTrue(Path(paths["items_csv"]).exists())
            self.assertTrue(Path(paths["items_json"]).exists())
            self.assertTrue(Path(paths["by_document_json"]).exists())

    def test_stop_source_inventory_exports_selected_stop_source_group(self):
        audit = {
            "document_id": "RATECON_INTERNAL_001",
            "file_hash": "hash-handoff",
            "file_name": "handoff.pdf",
            "private_eval_values": {
                "shadow_selected_stop": {
                    FIELD_PICKUP_STOPS: {
                        "value": [{"city": "Dallas", "state": "TX"}],
                        "source": "stop_evidence_assembler",
                        "parser_name": "stop_evidence_assembler",
                        "metadata_summary": {"stop_role": "pickup"},
                    }
                }
            },
        }
        source_inventory = build_stop_source_inventory_report(
            {},
            [audit],
            include_private_values=True,
        )

        self.assertEqual(source_inventory["items"][0]["source_group"], "shadow_selected_stop")
        trace = build_no_candidate_source_trace_summary(
            [
                {
                    "document_id": "DOC-HANDOFF",
                    "file_hash": "hash-handoff-full",
                    "file_name": "handoff.pdf",
                    "field": FIELD_PICKUP_STOPS,
                }
            ],
            source_inventory,
        )
        self.assertEqual(
            trace["reason_counts"]["selected_stop_comes_from_assembler_without_component_sources"],
            1,
        )

    def test_no_candidate_source_trace_uses_inventory_when_available(self):
        source_inventory = build_stop_source_inventory_report(
            {},
            [_source_inventory_audit_record()],
            include_private_values=False,
        )
        residual_items = [
            {
                "document_id": "DOC-HANDOFF",
                "file_hash": "hash-handoff",
                "file_name": "handoff.pdf",
                "field": FIELD_PICKUP_STOPS,
            }
        ]

        trace = build_no_candidate_source_trace_summary(residual_items, source_inventory)

        self.assertEqual(trace["issues_checked"], 1)
        self.assertEqual(trace["reason_counts"]["evaluator_only_missing_candidate_source"], 1)
        self.assertEqual(trace["unknown"], 0)

    def test_no_candidate_source_trace_matches_inventory_by_file_hash(self):
        audit = _source_inventory_audit_record()
        audit["document_id"] = "RATECON_INTERNAL_001"
        source_inventory = build_stop_source_inventory_report(
            {},
            [audit],
            include_private_values=False,
        )
        residual_items = [
            {
                "document_id": "DOC-HANDOFF",
                "file_hash": "hash-handoff",
                "file_name": "handoff.pdf",
                "field": FIELD_PICKUP_STOPS,
            }
        ]

        trace = build_no_candidate_source_trace_summary(residual_items, source_inventory)

        self.assertEqual(trace["reason_counts"]["evaluator_only_missing_candidate_source"], 1)
        self.assertEqual(trace["cases"][0]["inventory_entries_for_field"], 2)

    def test_no_candidate_source_trace_detects_inventory_omission_and_true_gap(self):
        generated_without_inventory = {
            "document_id": "DOC-HANDOFF",
            "file_hash": "hash-handoff",
            "file_name": "handoff.pdf",
            "candidate_counts_by_field": {FIELD_PICKUP_STOPS: 2},
            "private_eval_values": {"stop_component_candidate_inventory": []},
        }
        source_inventory = build_stop_source_inventory_report(
            {},
            [generated_without_inventory],
            include_private_values=False,
        )
        residual_items = [
            {
                "document_id": "DOC-HANDOFF",
                "file_hash": "hash-handoff",
                "file_name": "handoff.pdf",
                "field": FIELD_PICKUP_STOPS,
            },
            {
                "document_id": "DOC-MISSING",
                "file_hash": "hash-missing",
                "file_name": "missing.pdf",
                "field": FIELD_PICKUP_STOPS,
            },
        ]

        trace = build_no_candidate_source_trace_summary(residual_items, source_inventory)

        self.assertEqual(trace["reason_counts"]["component_candidate_generated_but_not_in_inventory"], 1)
        self.assertEqual(trace["reason_counts"]["true_no_source"], 1)
        self.assertEqual(trace["unknown"], 0)

    def test_residual_extraction_report_uses_source_inventory_context(self):
        packet = {
            "exclusive_category_counts": {},
            "items": [
                {
                    "document_id": "DOC-HANDOFF",
                    "file_hash": "hash-handoff",
                    "file_name": "handoff.pdf",
                    "field": FIELD_PICKUP_STOPS,
                    "categories": ["extraction_candidate_issue"],
                    "selected_stop_component_summary": {
                        "raw_status": "partial_match",
                        "dispatch_usability_tier": "useful_partial_location_only",
                    },
                    "selected_components": {},
                    "selected_source_hint": {},
                    "best_candidate_components": {},
                    "draft_components": {},
                    "gold_components": {},
                }
            ],
        }
        source_inventory = build_stop_source_inventory_report(
            {},
            [_source_inventory_audit_record()],
            include_private_values=False,
        )

        report = build_residual_extraction_report(packet, source_inventory_report=source_inventory)
        item = report["items"][0]

        self.assertEqual(item["selected_candidate_source"], "inventory:stop_evidence_assembler")
        self.assertEqual(item["source_inventory_match_count"], 2)
        self.assertNotIn(
            "no_candidate_source",
            report["stop_component_fusion_opportunity_summary"]["blocked_reason_counts"],
        )
        self.assertEqual(
            report["no_candidate_source_trace_summary"]["reason_counts"][
                "evaluator_only_missing_candidate_source"
            ],
            1,
        )

    def test_dedupe_provenance_summary_counts_missing_metadata(self):
        audit = _source_inventory_audit_record()
        audit["private_eval_values"]["stop_component_candidate_inventory"].append(
            {
                "candidate_id": "pickup-nosource",
                "field": FIELD_PICKUP_STOPS,
                "value": [{"city": "Dallas"}],
                "source": "",
                "parser_name": "",
                "metadata_summary": {},
            }
        )
        audit["private_eval_values"]["stop_component_candidate_inventory"].append(
            {
                "candidate_id": "",
                "field": FIELD_PICKUP_STOPS,
                "value": [{"city": "Fort Worth"}],
                "source": "native_text",
                "parser_name": "stop_evidence_assembler",
                "metadata_summary": {},
            }
        )
        report = build_stop_source_inventory_report({}, [audit], include_private_values=False)
        dedupe = report["stop_dedupe_provenance_loss_summary"]

        self.assertGreaterEqual(dedupe["lost_candidate_id_count"], 1)
        self.assertGreaterEqual(dedupe["merged_without_source_metadata"], 1)

    def test_candidate_has_dispatch_components_can_be_unsafe_against_gold(self):
        candidate = _dispatch_candidate()
        candidate["value"][0]["city"] = "Houston"
        candidate["value"][0]["facility"] = "Wrong Facility"
        candidates = apply_stop_column_strict_profile_to_candidates([candidate])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )
        audit = _audit_record(
            candidates,
            resolved,
            stop_draft_profile=STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
        )

        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        rows = [
            row
            for row in evaluation["comparison_rows"]
            if row["system"] == SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP
            and row["field"] == FIELD_PICKUP_STOPS
            and row.get("predicted")
        ]

        self.assertEqual(rows[0]["candidate_has_dispatch_components"], True)
        self.assertEqual(rows[0]["dispatch_usability_tier"], "unsafe_wrong")
        self.assertEqual(rows[0]["gold_dispatch_usable_match"], False)
        self.assertIn("structural only", rows[0]["dispatch_usability_note"])

    def test_stop_gold_completeness_counts_components(self):
        summary = build_stop_gold_completeness_summary([_gold_label()])

        pickup = summary["pickup"]
        self.assertEqual(pickup["stops_checked"], 1)
        self.assertEqual(pickup["component_present_counts"]["city"], 1)
        self.assertEqual(pickup["component_present_counts"]["date"], 1)
        self.assertEqual(pickup["component_present_counts"]["appointment_window"], 1)
        self.assertEqual(pickup["component_missing_counts"]["facility"], 1)
        self.assertEqual(pickup["complete_for_dispatch_usable"], 1)
        self.assertEqual(pickup["complete_for_exact"], 1)

    def test_stop_gold_patch_dry_run_uses_only_explicit_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gold_dir = Path(tmpdir)
            label_path = gold_dir / "handoff.gold.json"
            label_path.write_text(
                json.dumps(_gold_label()),
                encoding="utf-8",
            )
            patch = {
                "patches": [
                    {
                        "document_id": "DOC-HANDOFF",
                        "file_hash": "hash-handoff",
                        "file_name": "handoff.pdf",
                        "field": FIELD_PICKUP_STOPS,
                        "stop_index": 1,
                        "proposed_gold": {
                            "facility": None,
                            "address": "123 Main St",
                            "city": "",
                        },
                    }
                ]
            }

            planned, skipped = plan_stop_gold_patch(gold_dir, patch)

            self.assertEqual(len(planned), 1)
            self.assertEqual(skipped, [])
            self.assertEqual(planned[0]["updates"], {"address": "123 Main St"})
            self.assertNotIn("facility", planned[0]["updates"])

    def test_stop_gold_patch_refuses_unsafe_paths_without_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(SystemExit):
                _require_safe_path(Path(tmpdir), "gold dir")


if __name__ == "__main__":
    unittest.main()
