import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.ratecon_shadow_audit import (
    CODE_ARTIFACT_EMPTY,
    CODE_CONFLICTING_TOTAL_RATE_CANDIDATES,
    CODE_DOC_EMPTY_OR_LOW_TEXT,
    CODE_LEGACY_ONLY_FIELD,
    CODE_LOAD_LABEL_HIT_VALUE_REJECTED,
    CODE_LOAD_HIGH_QUALITY_CANDIDATE_NOT_SELECTED,
    CODE_PARTIAL_STOP_EVIDENCE_ONLY,
    CODE_MISSING_LOAD_NUMBER_CANDIDATE,
    CODE_REVIEW_GATE_LOAD_MISSING,
    CODE_REVIEW_GATE_STOP_PRESENT_PARTIAL,
    CODE_RESOLVER_IGNORED_HIGH_QUALITY_CANDIDATE,
    CODE_STOP_ASSEMBLY_FAILED,
    CODE_STOP_CANDIDATES_PARTIAL_ONLY,
    CODE_STOP_STRUCTURED_SELECTED_PARTIAL_REVIEW,
    CODE_STOP_TABLE_ROW_CANDIDATE_NOT_SELECTED,
    CODE_SHADOW_ONLY_FIELD,
    COMPARISON_DIFFERENT,
    COMPARISON_LEGACY_ONLY,
    COMPARISON_SAME,
    COMPARISON_SHADOW_ONLY,
    LAYER_CANDIDATE_GENERATION,
    LAYER_RESOLUTION,
    LAYER_TEXT_EXTRACTION,
    assign_failure_attribution,
    build_candidate_summary,
    build_legacy_summary_from_resolution,
    build_load_number_selection_summary,
    build_ratecon_shadow_audit_record,
    build_resolver_selection_summary,
    build_rate_review_sanity_summary,
    build_stop_selection_summary,
    build_structured_stop_conflict_summary,
    build_structured_stop_resolution_summary,
    compare_legacy_shadow,
    review_gate_trace_summary,
    summarize_ratecon_shadow_audit_records,
    write_ratecon_shadow_audit_artifacts,
)


class RateConShadowAuditTests(unittest.TestCase):
    def test_legacy_shadow_load_number_normalized_same(self):
        legacy = {
            "_comparison_values": {
                "load_number": " FAKE-LOAD-001 ",
                "total_carrier_rate": "$1,200.00",
            }
        }
        shadow = {
            "load_number": "fake-load-001",
            "total_carrier_rate": "1200.00",
        }

        comparison = compare_legacy_shadow(legacy, shadow)

        self.assertEqual(comparison["load_number"], COMPARISON_SAME)
        self.assertEqual(comparison["total_carrier_rate"], COMPARISON_SAME)

    def test_legacy_shadow_comparison_statuses(self):
        legacy = {
            "_comparison_values": {
                "load_number": "LOAD-A",
                "total_carrier_rate": "1000.00",
                "broker_name": "Fake Broker",
            }
        }
        shadow = {
            "load_number": "LOAD-B",
            "carrier_name": "Fake Carrier",
        }

        comparison = compare_legacy_shadow(legacy, shadow)

        self.assertEqual(comparison["load_number"], COMPARISON_DIFFERENT)
        self.assertEqual(comparison["total_carrier_rate"], COMPARISON_LEGACY_ONLY)
        self.assertEqual(comparison["carrier_name"], COMPARISON_SHADOW_ONLY)

    def test_failure_attribution_low_text_and_missing_candidates(self):
        result = assign_failure_attribution(
            triage={
                "quality_flags": ["EMPTY_OR_LOW_TEXT"],
                "ocr_required": False,
            },
            artifact_summary={
                "full_text_present": False,
                "full_text_length": 0,
                "line_count": 0,
                "table_count": 0,
            },
            candidate_summary={
                "total_candidates": 0,
                "candidates_by_field": {},
            },
            resolved_result={"resolved_fields": {}, "needs_review": True},
        )

        self.assertIn(CODE_DOC_EMPTY_OR_LOW_TEXT, result["codes"])
        self.assertIn(CODE_ARTIFACT_EMPTY, result["codes"])
        self.assertIn(CODE_MISSING_LOAD_NUMBER_CANDIDATE, result["codes"])
        self.assertEqual(result["primary_suspected_layer"], LAYER_TEXT_EXTRACTION)

    def test_failure_attribution_missing_candidate_generation_layer(self):
        result = assign_failure_attribution(
            triage={"quality_flags": [], "ocr_required": False},
            artifact_summary={
                "full_text_present": True,
                "full_text_length": 500,
                "line_count": 10,
                "table_count": 0,
            },
            candidate_summary={
                "total_candidates": 2,
                "candidates_by_field": {"broker_name": 1, "total_carrier_rate": 1},
            },
            resolved_result={"resolved_fields": {}, "needs_review": True},
        )

        self.assertIn(CODE_MISSING_LOAD_NUMBER_CANDIDATE, result["codes"])
        self.assertEqual(result["primary_suspected_layer"], LAYER_CANDIDATE_GENERATION)

    def test_failure_attribution_adds_specific_load_and_stop_evidence_codes(self):
        result = assign_failure_attribution(
            triage={"quality_flags": [], "ocr_required": False},
            artifact_summary={
                "full_text_present": True,
                "full_text_length": 500,
                "line_count": 10,
                "table_count": 0,
            },
            candidate_summary={
                "total_candidates": 2,
                "candidates_by_field": {"pickup_location": 1, "total_carrier_rate": 1},
                "stop_assembly_summary": {
                    "stop_evidence_count": 2,
                    "partial_stop_candidate_count": 1,
                    "assembled_pickup_stop_candidate_count": 0,
                    "assembled_delivery_stop_candidate_count": 0,
                },
                "load_identity_line_summary": {
                    "label_hits": 2,
                    "emitted_candidates": 0,
                    "skipped_by_reason": {"candidate_looks_like_date": 2},
                },
            },
            resolved_result={"resolved_fields": {}, "needs_review": True},
        )

        self.assertIn(CODE_LOAD_LABEL_HIT_VALUE_REJECTED, result["codes"])
        self.assertIn(CODE_PARTIAL_STOP_EVIDENCE_ONLY, result["codes"])
        self.assertIn(CODE_STOP_ASSEMBLY_FAILED, result["codes"])

    def test_failure_attribution_conflicting_total_rate(self):
        result = assign_failure_attribution(
            triage={"quality_flags": [], "ocr_required": False},
            artifact_summary={
                "full_text_present": True,
                "full_text_length": 500,
                "line_count": 10,
                "table_count": 0,
            },
            candidate_summary={
                "total_candidates": 4,
                "candidates_by_field": {
                    "load_number": 1,
                    "total_carrier_rate": 2,
                    "pickup_stops": 1,
                    "delivery_stops": 1,
                },
            },
            resolved_result={
                "resolved_fields": {
                    "load_number": {"value": "FAKE-LOAD-1", "review_reasons": []},
                    "total_carrier_rate": {
                        "value": "",
                        "review_reasons": ["CONFLICTING_CANDIDATES"],
                    },
                },
                "needs_review": True,
            },
        )

        self.assertIn(CODE_CONFLICTING_TOTAL_RATE_CANDIDATES, result["codes"])

    def test_build_shadow_audit_record_redacts_values_by_default(self):
        shadow_result = {
            "final_output": {
                "load_number": "FAKE-LOAD-1",
                "total_carrier_rate": "1234.00",
                "needs_review": False,
            },
            "needs_review": False,
            "review_reasons": [],
            "debug": {
                "triage": {
                    "pdf_type": "born_digital",
                    "page_count": 1,
                    "native_text_available": True,
                    "native_text_token_count": 20,
                    "quality_flags": [],
                    "routing_decision": "native_layout",
                    "ocr_required": False,
                },
                "artifact_summary": {
                    "source": "native",
                    "page_count": 1,
                    "line_count": 2,
                    "word_count": 0,
                    "table_count": 0,
                    "full_text_length": 100,
                    "full_text_present": True,
                },
                "candidates": [
                    {"field": "load_number", "source": "native_text"},
                    {"field": "total_carrier_rate", "source": "native_text"},
                ],
                "resolved_fields": {
                    "load_number": {
                        "value": "FAKE-LOAD-1",
                        "confidence": 0.9,
                        "evidence_text": "Load # FAKE-LOAD-1",
                        "candidate_count": 1,
                    }
                },
            },
        }
        legacy = build_legacy_summary_from_resolution(include_values=False)

        record = build_ratecon_shadow_audit_record(
            "RATECON_001",
            "fake.pdf",
            shadow_result,
            legacy_summary=legacy,
            include_values=False,
        )
        payload = json.dumps(record)

        self.assertIn("triage", record)
        self.assertIn("artifact_summary", record)
        self.assertIn("candidate_summary", record)
        self.assertIn("failure_attribution", record)
        self.assertNotIn("FAKE-LOAD-1", payload)
        self.assertFalse(record["private_values_included"])

    def test_candidate_summary_counts_fields_and_sources(self):
        summary = build_candidate_summary(
            [
                {
                    "field": "load_number",
                    "source": "native_text",
                    "parser_name": "gen_a",
                    "metadata": {"generator_name": "gen_a"},
                },
                {
                    "field": "load_number",
                    "source": "native_layout",
                    "parser_name": "gen_b",
                    "metadata": {"generator_name": "gen_b"},
                },
                {
                    "field": "total_carrier_rate",
                    "source": "legacy_final_output",
                    "parser_name": "legacy_final_output_adapter",
                    "metadata": {
                        "generator_name": "legacy_final_output_adapter",
                        "diagnostic_fallback": True,
                    },
                },
                {
                    "field": "custom_signal",
                    "value": "FAKE-001",
                    "source": "native_text",
                    "parser_name": "gen_c",
                    "metadata": {
                        "generator_name": "gen_c",
                        "raw_field": "custom_signal",
                        "canonical_mapping_strength": "unmapped",
                    },
                },
            ]
        )

        self.assertEqual(summary["total_candidates"], 4)
        self.assertEqual(summary["candidates_by_field"]["load_number"], 2)
        self.assertEqual(summary["candidates_by_source"]["native_text"], 2)
        self.assertEqual(summary["candidates_by_generator"]["gen_a"], 1)
        self.assertEqual(summary["independent_candidate_count"], 3)
        self.assertEqual(summary["legacy_final_fallback_candidate_count"], 1)
        self.assertEqual(
            summary["legacy_final_fallback_candidates_by_field"]["total_carrier_rate"],
            1,
        )
        self.assertIn("canonical_mapping_summary", summary)
        self.assertEqual(
            summary["canonical_mapping_summary"]["unmapped_raw_fields_top"][
                "custom_signal"
            ],
            1,
        )
        self.assertIn("candidate_taxonomy", summary)
        self.assertIn("stop_assembly_summary", summary)
        self.assertIn("load_identity_line_summary", summary)

    def test_candidate_summary_includes_layout_pairing_summaries(self):
        summary = build_candidate_summary(
            [],
            generator_summaries=[
                {
                    "generator_name": "layout_candidate_result_adapter",
                    "diagnostics": {
                        "table_extraction_summary": {
                            "docs_with_tables": 1,
                            "tables_detected": 2,
                            "tables_with_stop_like_headers": 1,
                            "tables_with_rate_like_headers": 1,
                            "tables_with_load_like_headers": 1,
                            "recognized_stop_tables": 1,
                            "recognized_load_tables": 1,
                            "recognized_rate_tables": 0,
                            "unrecognized_tables": 0,
                            "table_header_role_counts": {"load_identity": 1},
                            "table_row_role_counts": {"stop_role": 2},
                            "table_rows_with_stop_role": 2,
                            "table_rows_with_date_time_location": 1,
                        }
                    },
                },
                {
                    "generator_name": "layout_load_identity_pairing_generator",
                    "diagnostics": {
                        "layout_load_pairing_summary": {
                            "layout_label_hits": 2,
                            "same_row_pairings": 1,
                            "nearby_row_pairings": 0,
                            "table_cell_pairings": 1,
                            "header_block_pairings": 0,
                            "layout_candidates_emitted": 2,
                            "table_load_label_hits": 1,
                            "table_pairings_by_method": {
                                "table_key_value_row": 1
                            },
                            "layout_rejection_reason_counts": {
                                "LAYOUT_LOAD_LABEL_NO_RIGHT_VALUE": 1
                            },
                        }
                    },
                },
                {
                    "generator_name": "layout_stop_table_candidate_generator",
                    "diagnostics": {
                        "layout_stop_pairing_summary": {
                            "layout_stop_evidence_count": 4,
                            "layout_structured_stop_candidates": 2,
                            "table_row_stop_candidates": 2,
                            "bbox_cluster_stop_candidates": 0,
                            "table_stop_candidates_complete": 1,
                            "table_stop_candidates_partial": 1,
                            "table_pairings_by_method": {
                                "table_row_semantic": 2
                            },
                            "layout_ambiguity_reason_counts": {
                                "LAYOUT_STOP_ROLE_AMBIGUOUS": 1
                            },
                        }
                    },
                },
            ],
        )

        self.assertEqual(summary["table_extraction_summary"]["tables_detected"], 2)
        self.assertEqual(
            summary["table_profile_summary"]["recognized_load_tables"],
            1,
        )
        self.assertEqual(
            summary["layout_load_pairing_summary"]["table_cell_pairings"],
            1,
        )
        self.assertEqual(
            summary["layout_load_pairing_summary"]["table_pairings_by_method"][
                "table_key_value_row"
            ],
            1,
        )
        self.assertEqual(
            summary["layout_stop_pairing_summary"]["layout_structured_stop_candidates"],
            2,
        )
        self.assertEqual(
            summary["layout_stop_pairing_summary"]["table_stop_candidates_complete"],
            1,
        )

    def test_candidate_quality_counts_dedup_and_bands(self):
        summary = build_candidate_summary(
            [
                {
                    "field": "load_number",
                    "value": "FAKE123",
                    "normalized_value": "FAKE123",
                    "source": "native_layout",
                    "parser_name": "layout_load_identity_pairing_generator",
                    "confidence": 0.86,
                    "metadata": {
                        "generator_name": "layout_load_identity_pairing_generator",
                        "pairing_method": "table_key_value_row",
                        "table_index": 0,
                        "row_index": 1,
                    },
                },
                {
                    "field": "load_number",
                    "value": "FAKE123",
                    "normalized_value": "FAKE123",
                    "source": "native_layout",
                    "parser_name": "layout_load_identity_pairing_generator",
                    "confidence": 0.86,
                    "metadata": {
                        "generator_name": "layout_load_identity_pairing_generator",
                        "pairing_method": "table_key_value_row",
                        "table_index": 0,
                        "row_index": 1,
                    },
                },
                {
                    "field": "pickup_stops",
                    "value": "pickup_layout_stop_present",
                    "source": "native_layout",
                    "parser_name": "layout_stop_table_candidate_generator",
                    "confidence": 0.55,
                    "metadata": {
                        "generator_name": "layout_stop_table_candidate_generator",
                        "structured_stop_candidate": True,
                        "partial_stop_candidate": True,
                    },
                },
            ]
        )

        quality = summary["candidate_quality_summary"]

        self.assertEqual(quality["duplicate_candidates_removed"], 1)
        self.assertEqual(
            quality["critical_fields_with_high_quality_independent_candidates"][
                "load_number"
            ],
            2,
        )
        self.assertEqual(
            quality["critical_fields_with_only_weak_candidates"]["pickup_stops"],
            1,
        )

    def test_resolver_selection_summaries_count_safe_reasons(self):
        traces = {
            "load_number": {
                "selected_candidate": {},
                "candidate_count_seen": 2,
                "candidate_count_eligible": 2,
                "candidate_count_ineligible": 0,
                "candidates_by_quality_band": {"high": 1, "weak": 1},
                "top_rejected_or_not_selected": [
                    {
                        "quality_band": "high",
                        "reason": "lower_confidence",
                    }
                ],
                "decision_status": "review_required",
            },
            "pickup_stops": {
                "selected_candidate": {},
                "candidate_count_seen": 1,
                "candidate_count_eligible": 1,
                "candidate_count_ineligible": 0,
                "candidates_by_quality_band": {"weak": 1},
                "top_rejected_or_not_selected": [
                    {
                        "reason": "partial_only",
                        "metadata_summary": {
                            "structured_stop_candidate": True,
                            "partial_stop_candidate": True,
                            "has_location": True,
                            "pairing_method": "table_row_semantic",
                        },
                    }
                ],
                "decision_status": "low_confidence",
            },
        }

        resolver_summary = build_resolver_selection_summary(traces)
        load_summary = build_load_number_selection_summary(traces)
        stop_summary = build_stop_selection_summary(traces)

        self.assertEqual(
            resolver_summary["fields"]["load_number"]["candidate_count_seen"],
            2,
        )
        self.assertEqual(
            resolver_summary["fields"]["load_number"][
                "high_quality_not_selected_count"
            ],
            1,
        )
        self.assertEqual(load_summary["docs_with_any_load_candidates"], 1)
        self.assertEqual(
            load_summary["docs_with_load_candidates_but_no_selection"],
            1,
        )
        self.assertEqual(
            stop_summary["pickup"]["docs_with_partial_structured_candidates"],
            1,
        )
        self.assertEqual(
            stop_summary["pickup"]["not_selected_reason_counts"]["partial_only"],
            1,
        )

    def test_review_gate_trace_summary_counts_statuses(self):
        summary = review_gate_trace_summary(
            {
                "needs_review": True,
                "critical_field_status": {
                    "load_number": {"status": "missing"},
                    "total_carrier_rate": {"status": "low_confidence"},
                },
                "review_reason_sources": {
                    "missing_field": ["load_number"],
                    "low_confidence": ["total_carrier_rate"],
                },
            }
        )

        self.assertEqual(summary["needs_review_count"], 1)
        self.assertEqual(
            summary["critical_field_status_counts"]["load_number:missing"],
            1,
        )
        self.assertEqual(summary["review_reason_source_counts"]["missing_field"], 1)

    def test_structured_stop_resolution_summary_counts_partial_and_conflicts(self):
        resolved = {
            "pickup_stops": {
                "value": "pickup_stop_useful_partial",
                "structure_status": "useful_partial",
                "selected_status": "selected_useful_partial",
                "structured_stop_conflict_summary": {
                    "normalized_candidate_count": 2,
                    "duplicates_collapsed": 1,
                    "true_conflict_count": 0,
                    "partial_overlap_count": 1,
                    "selected_status": "selected_useful_partial",
                    "conflict_type_counts": {},
                },
            },
            "delivery_stops": {
                "value": "delivery_stop_complete",
                "structure_status": "complete",
                "selected_status": "conflict",
                "structured_stop_conflict_summary": {
                    "normalized_candidate_count": 2,
                    "duplicates_collapsed": 0,
                    "true_conflict_count": 1,
                    "partial_overlap_count": 0,
                    "selected_status": "conflict",
                    "conflict_type_counts": {"date_conflict": 1},
                },
            },
        }

        resolution = build_structured_stop_resolution_summary(resolved)
        conflict = build_structured_stop_conflict_summary(resolved)

        self.assertEqual(resolution["pickup"]["docs_selected_partial"], 1)
        self.assertEqual(resolution["pickup"]["duplicates_collapsed"], 1)
        self.assertEqual(resolution["delivery"]["docs_conflict_review"], 1)
        self.assertEqual(
            conflict["delivery_stops"]["conflict_type_counts"]["date_conflict"],
            1,
        )

    def test_rate_review_sanity_flags_selected_rate_marked_missing(self):
        summary = build_rate_review_sanity_summary(
            {
                "total_carrier_rate": {
                    "value": "FAKE-RATE",
                    "candidate_count": 2,
                    "selected_candidate": {"source": "native_text"},
                    "review_reasons": [],
                }
            },
            {
                "critical_field_status": {
                    "total_carrier_rate": {"status": "missing"}
                }
            },
        )

        self.assertEqual(summary["docs_with_selected_rate"], 1)
        self.assertEqual(summary["rate_review_mismatch_count"], 1)
        self.assertEqual(
            summary["mismatch_reasons"]["selected_rate_marked_missing"],
            1,
        )

    def test_failure_attribution_moves_ignored_high_quality_to_resolution(self):
        result = assign_failure_attribution(
            triage={"quality_flags": [], "ocr_required": False},
            artifact_summary={
                "full_text_present": True,
                "full_text_length": 500,
                "line_count": 10,
                "table_count": 1,
            },
            candidate_summary={
                "total_candidates": 3,
                "candidates_by_field": {
                    "load_number": 2,
                    "total_carrier_rate": 1,
                    "pickup_stops": 1,
                    "delivery_stops": 1,
                },
                "resolver_selection_summary": {
                    "fields": {
                        "load_number": {
                            "candidate_count_seen": 2,
                            "eligible_count": 2,
                            "high_quality_not_selected_count": 1,
                            "not_selected_reason_counts": {"lower_confidence": 1},
                        }
                    }
                },
                "load_number_selection_summary": {
                    "docs_with_any_load_candidates": 1,
                },
                "review_gate_trace_summary": {
                    "critical_field_status_counts": {},
                },
            },
            resolved_result={"resolved_fields": {}, "needs_review": True},
        )

        self.assertIn(CODE_RESOLVER_IGNORED_HIGH_QUALITY_CANDIDATE, result["codes"])
        self.assertIn(CODE_LOAD_HIGH_QUALITY_CANDIDATE_NOT_SELECTED, result["codes"])
        self.assertEqual(result["primary_suspected_layer"], LAYER_RESOLUTION)

    def test_failure_attribution_keeps_partial_stops_as_candidate_quality(self):
        result = assign_failure_attribution(
            triage={"quality_flags": [], "ocr_required": False},
            artifact_summary={
                "full_text_present": True,
                "full_text_length": 500,
                "line_count": 10,
                "table_count": 1,
            },
            candidate_summary={
                "total_candidates": 3,
                "candidates_by_field": {
                    "load_number": 1,
                    "total_carrier_rate": 1,
                    "pickup_stops": 1,
                    "delivery_stops": 1,
                },
                "stop_selection_summary": {
                    "pickup": {
                        "docs_with_any_candidates": 1,
                        "docs_with_partial_structured_candidates": 1,
                        "docs_with_complete_structured_candidates": 0,
                        "docs_with_table_row_candidates": 1,
                        "docs_with_selected_candidates": 0,
                    }
                },
                "review_gate_trace_summary": {
                    "critical_field_status_counts": {},
                },
            },
            resolved_result={"resolved_fields": {}, "needs_review": True},
        )

        self.assertIn(CODE_STOP_TABLE_ROW_CANDIDATE_NOT_SELECTED, result["codes"])
        self.assertIn(CODE_STOP_CANDIDATES_PARTIAL_ONLY, result["codes"])

    def test_failure_attribution_adds_review_gate_codes(self):
        result = assign_failure_attribution(
            triage={"quality_flags": [], "ocr_required": False},
            artifact_summary={
                "full_text_present": True,
                "full_text_length": 500,
                "line_count": 10,
                "table_count": 1,
            },
            candidate_summary={
                "total_candidates": 3,
                "candidates_by_field": {
                    "total_carrier_rate": 1,
                    "pickup_stops": 1,
                    "delivery_stops": 1,
                },
                "review_gate_trace_summary": {
                    "critical_field_status_counts": {
                        "load_number:missing": 1,
                    },
                },
            },
            resolved_result={"resolved_fields": {}, "needs_review": True},
        )

        self.assertIn(CODE_REVIEW_GATE_LOAD_MISSING, result["codes"])

    def test_failure_attribution_moves_selected_partial_stop_to_validation(self):
        result = assign_failure_attribution(
            triage={"quality_flags": [], "ocr_required": False},
            artifact_summary={
                "full_text_present": True,
                "full_text_length": 500,
                "line_count": 10,
                "table_count": 1,
            },
            candidate_summary={
                "total_candidates": 3,
                "candidates_by_field": {
                    "load_number": 1,
                    "total_carrier_rate": 1,
                    "pickup_stops": 1,
                    "delivery_stops": 1,
                },
                "structured_stop_resolution_summary": {
                    "pickup": {
                        "docs_with_structured_candidates": 1,
                        "docs_selected_partial": 1,
                    }
                },
                "review_gate_trace_summary": {
                    "critical_field_status_counts": {
                        "pickup_stops:partial_review_required": 1,
                    },
                },
            },
            resolved_result={"resolved_fields": {}, "needs_review": True},
        )

        self.assertIn(CODE_STOP_STRUCTURED_SELECTED_PARTIAL_REVIEW, result["codes"])
        self.assertIn(CODE_REVIEW_GATE_STOP_PRESENT_PARTIAL, result["codes"])
        self.assertEqual(result["primary_suspected_layer"], "validation")

    def test_batch_summary_counts_review_and_failure_layers(self):
        records = [
            {
                "shadow": {
                    "success": True,
                    "needs_review": True,
                    "review_reasons": ["MISSING_CRITICAL_FIELD:load_number"],
                },
                "triage": {
                    "pdf_type": "born_digital",
                    "ocr_required": False,
                    "quality_flags": [],
                },
                "candidate_summary": {
                    "candidates_by_field": {"total_carrier_rate": 1},
                    "independent_candidates_by_field": {"total_carrier_rate": 1},
                    "legacy_final_fallback_candidates_by_field": {},
                    "candidates_by_generator": {"gen_a": 1},
                    "canonical_mapping_summary": {
                        "mapped_by_strength": {"strong": 1},
                        "critical_field_candidates_by_mapping_strength": {
                            "total_carrier_rate": {"strong": 1}
                        },
                    },
                    "candidate_taxonomy": {
                        "raw_fields_by_generator": {"gen_a": {"rate": 1}},
                        "canonical_fields_by_generator": {
                            "gen_a": {"total_carrier_rate": 1}
                        },
                    },
                    "stop_assembly_summary": {
                        "stop_evidence_count": 2,
                        "stop_evidence_by_role": {"pickup": 1, "delivery": 1},
                        "stop_evidence_by_type": {"date": 2},
                        "assembled_pickup_stop_candidate_count": 1,
                        "assembled_delivery_stop_candidate_count": 0,
                        "docs_with_assembled_pickup_stops": 1,
                        "docs_with_assembled_delivery_stops": 0,
                        "partial_stop_candidate_count": 1,
                        "ambiguous_stop_candidate_count": 0,
                    },
                    "load_identity_line_summary": {
                        "lines_scanned": 5,
                        "label_hits": 1,
                        "emitted_candidates": 0,
                        "skipped_by_reason": {"candidate_looks_like_date": 1},
                        "emitted_by_method": {},
                    },
                },
                "legacy_shadow_comparison": {"load_number": COMPARISON_LEGACY_ONLY},
                "failure_attribution": {
                    "primary_suspected_layer": "candidate_generation",
                    "codes": [CODE_MISSING_LOAD_NUMBER_CANDIDATE, CODE_LEGACY_ONLY_FIELD],
                },
            },
            {
                "shadow": {
                    "success": True,
                    "needs_review": False,
                    "review_reasons": [],
                },
                "triage": {
                    "pdf_type": "born_digital",
                    "ocr_required": False,
                    "quality_flags": [],
                },
                "candidate_summary": {
                    "candidates_by_field": {"load_number": 1},
                    "independent_candidates_by_field": {},
                    "legacy_final_fallback_candidates_by_field": {"load_number": 1},
                    "candidates_by_generator": {"legacy_final_output_adapter": 1},
                    "canonical_mapping_summary": {
                        "mapped_by_strength": {"strong": 1},
                        "critical_field_candidates_by_mapping_strength": {
                            "load_number": {"strong": 1}
                        },
                    },
                    "candidate_taxonomy": {
                        "raw_fields_by_generator": {
                            "legacy_final_output_adapter": {"load_number": 1}
                        },
                        "canonical_fields_by_generator": {
                            "legacy_final_output_adapter": {"load_number": 1}
                        },
                    },
                },
                "legacy_shadow_comparison": {"load_number": COMPARISON_SHADOW_ONLY},
                "failure_attribution": {
                    "primary_suspected_layer": "legacy_parser",
                    "codes": [CODE_SHADOW_ONLY_FIELD],
                },
            },
        ]

        summary = summarize_ratecon_shadow_audit_records(records)

        self.assertEqual(summary["documents_processed"], 2)
        self.assertEqual(summary["shadow_success"], 2)
        self.assertEqual(summary["review_gate"]["needs_review_count"], 1)
        self.assertEqual(
            summary["failure_attribution"]["primary_layer_counts"]["candidate_generation"],
            1,
        )
        self.assertEqual(
            summary["legacy_vs_shadow"]["legacy_only_counts"]["load_number"],
            1,
        )
        self.assertEqual(
            summary["candidate_generation"]["generator_candidate_counts"][
                "legacy_final_output_adapter"
            ],
            1,
        )
        self.assertEqual(
            summary["candidate_generation"]["canonical_mapping_summary"][
                "mapped_by_strength"
            ]["strong"],
            2,
        )
        self.assertEqual(
            summary["candidate_generation"]["stop_assembly_summary"][
                "stop_evidence_count"
            ],
            2,
        )
        self.assertEqual(
            summary["candidate_generation"]["load_identity_line_summary"][
                "label_hits"
            ],
            1,
        )

    def test_writer_outputs_jsonl_and_summary(self):
        record = {
            "document_id": "RATECON_001",
            "shadow": {"success": False, "needs_review": True, "review_reasons": []},
            "triage": {"pdf_type": "unknown", "quality_flags": []},
            "candidate_summary": {"candidates_by_field": {}},
            "legacy_shadow_comparison": {},
            "failure_attribution": {
                "primary_suspected_layer": "unknown",
                "codes": [],
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            result = write_ratecon_shadow_audit_artifacts(
                [record],
                output_dir=temp_dir,
                allow_custom_output_dir=True,
            )
            jsonl_path = Path(temp_dir) / result["files"]["ratecon_shadow_audit_jsonl"]
            summary_path = Path(temp_dir) / result["files"]["ratecon_shadow_summary_json"]

            jsonl_lines = jsonl_path.read_text(encoding="utf-8").splitlines()
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(len(jsonl_lines), 1)
        self.assertEqual(summary["documents_processed"], 1)


if __name__ == "__main__":
    unittest.main()
