import csv
import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.ratecon_shadow_root_cause_analysis import (
    FIELD_DELIVERY_STOPS,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
    FIELD_TOTAL_RATE,
    analyze_ratecon_shadow_audit,
    load_shadow_audit_jsonl,
    load_shadow_summary,
    write_ratecon_shadow_root_cause_artifacts,
)


def fake_record(
    document_id,
    layer="candidate_generation",
    codes=None,
    needs_review=True,
    comparisons=None,
    candidates=None,
    independent_candidates=None,
    fallback_candidates=None,
    generators=None,
    mapping=None,
    taxonomy=None,
    stop_summary=None,
    load_line_summary=None,
    layout_provider_summary=None,
    table_summary=None,
    layout_load_summary=None,
    layout_stop_summary=None,
    pdf_type="born_digital",
):
    return {
        "document_id": document_id,
        "file_name": "",
        "file_hash": "",
        "shadow": {
            "success": True,
            "needs_review": needs_review,
            "review_reasons": ["MISSING_CRITICAL_FIELD:load_number"] if needs_review else [],
            "resolved_fields": {},
        },
        "triage": {
            "pdf_type": pdf_type,
            "page_count": 1,
            "quality_flags": [],
        },
        "candidate_summary": {
            "total_candidates": sum((candidates or {}).values()),
            "candidates_by_field": candidates or {},
            "candidates_by_source": {},
            "candidates_by_generator": generators or {},
            "independent_candidates_by_field": (
                candidates or {} if independent_candidates is None else independent_candidates
            ),
            "legacy_final_fallback_candidates_by_field": fallback_candidates or {},
            "canonical_mapping_summary": mapping
            or {
                "mapped_by_strength": {},
                "unmapped_raw_fields_top": {},
                "critical_field_candidates_by_mapping_strength": {},
                "independent_critical_field_candidates_by_mapping_strength": {},
                "legacy_final_critical_field_candidates_by_mapping_strength": {},
            },
            "candidate_taxonomy": taxonomy
            or {
                "raw_fields_by_generator": {},
                "canonical_fields_by_generator": {},
                "structured_stop_candidates_by_field": {},
                "partial_stop_candidates_by_field": {},
                "generator_summaries": [],
            },
            "stop_assembly_summary": stop_summary
            or {
                "stop_evidence_count": 0,
                "stop_evidence_by_role": {},
                "stop_evidence_by_type": {},
                "assembled_pickup_stop_candidate_count": 0,
                "assembled_delivery_stop_candidate_count": 0,
                "docs_with_assembled_pickup_stops": 0,
                "docs_with_assembled_delivery_stops": 0,
                "partial_stop_candidate_count": 0,
                "ambiguous_stop_candidate_count": 0,
            },
            "load_identity_line_summary": load_line_summary
            or {
                "lines_scanned": 0,
                "label_hits": 0,
                "emitted_candidates": 0,
                "skipped_by_reason": {},
                "emitted_by_method": {},
            },
            "table_extraction_summary": table_summary
            or {
                "docs_with_tables": 0,
                "tables_detected": 0,
                "tables_with_stop_like_headers": 0,
                "tables_with_rate_like_headers": 0,
                "tables_with_load_like_headers": 0,
                "recognized_stop_tables": 0,
                "recognized_load_tables": 0,
                "recognized_rate_tables": 0,
                "unrecognized_tables": 0,
                "table_header_role_counts": {},
                "table_row_role_counts": {},
                "table_rows_with_stop_role": 0,
                "table_rows_with_date_time_location": 0,
            },
            "layout_load_pairing_summary": layout_load_summary
            or {
                "layout_label_hits": 0,
                "same_row_pairings": 0,
                "nearby_row_pairings": 0,
                "table_cell_pairings": 0,
                "header_block_pairings": 0,
                "layout_candidates_emitted": 0,
                "table_load_label_hits": 0,
                "table_pairings_by_method": {},
                "layout_rejection_reason_counts": {},
            },
            "layout_stop_pairing_summary": layout_stop_summary
            or {
                "layout_stop_evidence_count": 0,
                "layout_structured_stop_candidates": 0,
                "table_row_stop_candidates": 0,
                "bbox_cluster_stop_candidates": 0,
                "table_stop_candidates_complete": 0,
                "table_stop_candidates_partial": 0,
                "table_stop_candidates_ambiguous": 0,
                "table_pairings_by_method": {},
                "layout_ambiguity_reason_counts": {},
            },
            "candidate_quality_summary": {
                "duplicate_candidates_removed": 0,
                "critical_fields_with_high_quality_independent_candidates": {},
                "critical_fields_with_only_weak_candidates": {},
                "critical_fields_with_only_legacy_fallback": {},
            },
            "layout_candidate_effectiveness": {
                "layout_load_candidates": {
                    "emitted": 0,
                    "by_pairing_method": {},
                    "by_id_type_hint": {},
                    "by_confidence_band": {},
                    "accepted_by_resolver": 0,
                    "rejected_or_not_selected": 0,
                    "not_selected_reasons": {},
                },
                "layout_stop_candidates": {
                    "emitted": 0,
                    "structured": 0,
                    "partial": 0,
                    "by_pairing_method": {},
                    "with_location": 0,
                    "with_date": 0,
                    "with_time": 0,
                    "accepted_by_resolver": 0,
                    "rejected_or_not_selected": 0,
                    "ambiguity_reasons": {},
                },
            },
        },
        "artifact_summary": {
            "layout_provider_summary": layout_provider_summary
            or {
                "provider_requested": "native_text",
                "provider_used": "native_text",
                "available": True,
                "status": "native_text",
                "pages_with_words": 0,
                "pages_with_lines": 0,
                "pages_with_tables": 0,
                "word_count": 0,
                "line_count": 0,
                "table_count": 0,
                "table_cell_count": 0,
                "warnings": [],
                "errors": [],
            }
        },
        "legacy_shadow_comparison": comparisons or {},
        "failure_attribution": {
            "primary_suspected_layer": layer,
            "codes": codes or [],
        },
    }


class RateConShadowRootCauseAnalysisTests(unittest.TestCase):
    def test_analyzer_counts_failure_codes_layers_and_comparisons(self):
        records = [
            fake_record(
                "RATECON_001",
                codes=["MISSING_LOAD_NUMBER_CANDIDATE", "LEGACY_ONLY_FIELD"],
                comparisons={FIELD_LOAD_NUMBER: "legacy_only", FIELD_TOTAL_RATE: "same"},
                candidates={FIELD_TOTAL_RATE: 1},
            ),
            fake_record(
                "RATECON_002",
                layer="resolution",
                codes=["CONFLICTING_TOTAL_RATE_CANDIDATES"],
                comparisons={FIELD_LOAD_NUMBER: "same", FIELD_TOTAL_RATE: "different"},
                candidates={FIELD_LOAD_NUMBER: 1, FIELD_TOTAL_RATE: 2},
            ),
        ]

        analysis = analyze_ratecon_shadow_audit(audit_records=records, top_n=10)

        self.assertEqual(analysis["documents_processed"], 2)
        self.assertEqual(
            analysis["failure_code_counts"]["MISSING_LOAD_NUMBER_CANDIDATE"],
            1,
        )
        self.assertEqual(analysis["primary_layer_counts"]["candidate_generation"], 1)
        self.assertEqual(
            analysis["field_comparison_counts"][FIELD_TOTAL_RATE]["different"],
            1,
        )
        self.assertEqual(
            analysis["candidate_coverage"][FIELD_LOAD_NUMBER]["candidate_missing_count"],
            1,
        )

    def test_recommendation_prefers_candidate_generation_when_candidate_codes_dominate(self):
        records = [
            fake_record(
                f"RATECON_{index:03d}",
                codes=["MISSING_LOAD_NUMBER_CANDIDATE"],
                candidates={FIELD_TOTAL_RATE: 1},
            )
            for index in range(1, 5)
        ]

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertIn(
            "improve candidate generation",
            analysis["recommendation"]["primary_next_move"],
        )

    def test_recommendation_uses_dominant_document_family_not_first_matching_family(self):
        records = [
            fake_record(
                "RATECON_001",
                layer="text_extraction",
                codes=["DOC_EMPTY_OR_LOW_TEXT", "DOC_SCANNED_OR_OCR_REQUIRED"],
                candidates={},
            ),
            fake_record(
                "RATECON_002",
                layer="text_extraction",
                codes=["DOC_IMAGE_HEAVY"],
                candidates={},
            ),
            fake_record(
                "RATECON_003",
                codes=["MISSING_LOAD_NUMBER_CANDIDATE"],
                candidates={FIELD_TOTAL_RATE: 1},
            ),
            fake_record(
                "RATECON_004",
                codes=["MISSING_LOAD_NUMBER_CANDIDATE"],
                candidates={FIELD_TOTAL_RATE: 1},
            ),
            fake_record(
                "RATECON_005",
                codes=["MISSING_LOAD_NUMBER_CANDIDATE"],
                candidates={FIELD_TOTAL_RATE: 1},
            ),
            fake_record(
                "RATECON_006",
                codes=["MISSING_LOAD_NUMBER_CANDIDATE"],
                candidates={FIELD_TOTAL_RATE: 1},
            ),
        ]

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertEqual(
            analysis["failure_family_document_counts"]["candidate_generation"],
            4,
        )
        self.assertIn(
            "improve candidate generation",
            analysis["recommendation"]["primary_next_move"],
        )

    def test_recommendation_prefers_primary_layer_when_missing_candidates_cause_resolver_codes(self):
        records = [
            fake_record(
                f"RATECON_{index:03d}",
                layer="candidate_generation",
                codes=["MISSING_LOAD_NUMBER_CANDIDATE", "RESOLVER_NO_DECISION"],
                candidates={FIELD_TOTAL_RATE: 1},
            )
            for index in range(1, 5)
        ]

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertEqual(
            analysis["failure_family_document_counts"]["candidate_generation"],
            4,
        )
        self.assertEqual(analysis["failure_family_document_counts"]["resolution"], 4)
        self.assertIn(
            "improve candidate generation",
            analysis["recommendation"]["primary_next_move"],
        )

    def test_recommendation_selects_ocr_when_text_extraction_is_primary_layer(self):
        records = [
            fake_record(
                f"RATECON_{index:03d}",
                layer="text_extraction",
                codes=["DOC_EMPTY_OR_LOW_TEXT", "DOC_SCANNED_OR_OCR_REQUIRED"],
                candidates={},
                pdf_type="scanned",
            )
            for index in range(1, 5)
        ]

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertIn(
            "implement OCR",
            analysis["recommendation"]["primary_next_move"],
        )

    def test_analyzer_handles_missing_optional_fields(self):
        analysis = analyze_ratecon_shadow_audit(audit_records=[{"document_id": "RATECON_001"}])

        self.assertEqual(analysis["documents_processed"], 1)
        self.assertIn("unknown", analysis["primary_layer_counts"])
        self.assertFalse(analysis["raw_text_printed"])

    def test_jsonl_and_summary_loaders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path = root / "summary.json"
            audit_path = root / "audit.jsonl"
            summary_path.write_text('{"documents_processed": 1}', encoding="utf-8")
            audit_path.write_text(
                json.dumps(fake_record("RATECON_001")) + "\n",
                encoding="utf-8",
            )

            summary = load_shadow_summary(summary_path)
            records = load_shadow_audit_jsonl(audit_path)

        self.assertEqual(summary["documents_processed"], 1)
        self.assertEqual(len(records), 1)

    def test_writer_creates_markdown_json_and_csvs_without_text(self):
        records = [
            fake_record(
                "RATECON_001",
                codes=["MISSING_TOTAL_RATE_CANDIDATE"],
                candidates={FIELD_LOAD_NUMBER: 1},
            )
        ]
        analysis = analyze_ratecon_shadow_audit(audit_records=records)
        with tempfile.TemporaryDirectory() as temp_dir:
            result = write_ratecon_shadow_root_cause_artifacts(
                analysis,
                output_dir=temp_dir,
                allow_custom_output_dir=True,
            )
            files = result["files"]
            md_text = (Path(temp_dir) / files["root_cause_report_md"]).read_text(
                encoding="utf-8"
            )
            summary = json.loads(
                (Path(temp_dir) / files["root_cause_summary_json"]).read_text(
                    encoding="utf-8"
                )
            )
            with (Path(temp_dir) / files["failure_codes_csv"]).open(
                newline="",
                encoding="utf-8",
            ) as handle:
                rows = list(csv.DictReader(handle))

        self.assertIn("PRIMARY NEXT MOVE", md_text)
        self.assertEqual(summary["documents_processed"], 1)
        self.assertEqual(rows[0]["failure_code"], "MISSING_TOTAL_RATE_CANDIDATE")
        self.assertFalse(result["raw_text_printed"])

    def test_analyzer_reports_independent_and_fallback_candidate_coverage(self):
        records = [
            fake_record(
                "RATECON_001",
                candidates={FIELD_LOAD_NUMBER: 1},
                independent_candidates={FIELD_LOAD_NUMBER: 1},
                generators={"load_identifier_line_candidate_generator": 1},
            ),
            fake_record(
                "RATECON_002",
                candidates={FIELD_LOAD_NUMBER: 1},
                independent_candidates={},
                fallback_candidates={FIELD_LOAD_NUMBER: 1},
                generators={"legacy_final_output_adapter": 1},
            ),
        ]

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertEqual(
            analysis["candidate_coverage"][FIELD_LOAD_NUMBER]["candidate_present_count"],
            2,
        )
        self.assertEqual(
            analysis["independent_candidate_coverage"][FIELD_LOAD_NUMBER][
                "candidate_present_count"
            ],
            1,
        )
        self.assertEqual(
            analysis["legacy_final_fallback_candidate_coverage"][FIELD_LOAD_NUMBER][
                "candidate_present_count"
            ],
            1,
        )
        self.assertEqual(
            analysis["generator_candidate_counts"]["legacy_final_output_adapter"],
            1,
        )

    def test_analyzer_reports_canonical_mapping_and_line_diagnostics(self):
        records = [
            fake_record(
                "RATECON_001",
                candidates={FIELD_LOAD_NUMBER: 1},
                generators={"load_identifier_line_candidate_generator": 1},
                mapping={
                    "mapped_by_strength": {"medium": 1, "unmapped": 1},
                    "unmapped_raw_fields_top": {"custom_signal": 1},
                    "critical_field_candidates_by_mapping_strength": {
                        FIELD_LOAD_NUMBER: {"medium": 1}
                    },
                    "independent_critical_field_candidates_by_mapping_strength": {
                        FIELD_LOAD_NUMBER: {"medium": 1}
                    },
                    "legacy_final_critical_field_candidates_by_mapping_strength": {},
                },
                taxonomy={
                    "raw_fields_by_generator": {
                        "load_identifier_line_candidate_generator": {
                            "shipment_id": 1
                        }
                    },
                    "canonical_fields_by_generator": {
                        "load_identifier_line_candidate_generator": {
                            FIELD_LOAD_NUMBER: 1
                        }
                    },
                    "structured_stop_candidates_by_field": {},
                    "partial_stop_candidates_by_field": {},
                    "generator_summaries": [
                        {
                            "generator_name": "load_identifier_line_candidate_generator",
                            "diagnostics": {
                                "lines_scanned_count": 4,
                                "label_hits_count": 1,
                                "candidates_emitted_count": 1,
                                "skipped_reason_counts": {
                                    "value_shape_not_identifier_like": 1
                                },
                            },
                        }
                    ],
                },
            )
        ]

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        mapping = analysis["canonical_mapping_summary"]
        self.assertEqual(mapping["mapped_by_strength"]["medium"], 1)
        self.assertEqual(mapping["unmapped_raw_fields_top"]["custom_signal"], 1)
        self.assertEqual(
            mapping["raw_fields_by_generator"][
                "load_identifier_line_candidate_generator"
            ]["shipment_id"],
            1,
        )
        self.assertEqual(
            mapping["load_identifier_line_generator_diagnostics"][
                "lines_scanned_count"
            ],
            4,
        )
        self.assertEqual(
            analysis["independent_critical_document_coverage_by_strength"][
                FIELD_LOAD_NUMBER
            ]["medium"],
            1,
        )

    def test_analyzer_reports_structured_and_partial_stop_coverage(self):
        records = [
            fake_record(
                "RATECON_001",
                candidates={"pickup_stops": 1, "pickup_date": 1},
                taxonomy={
                    "raw_fields_by_generator": {},
                    "canonical_fields_by_generator": {},
                    "structured_stop_candidates_by_field": {"pickup_stops": 1},
                    "partial_stop_candidates_by_field": {"pickup_date": 1},
                    "generator_summaries": [],
                },
            )
        ]

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertEqual(
            analysis["stop_candidate_coverage"][
                "independent_structured_present_by_field"
            ]["pickup_stops"],
            1,
        )
        self.assertEqual(
            analysis["stop_candidate_coverage"][
                "independent_partial_present_by_field"
            ]["pickup_stops"],
            1,
        )

    def test_analyzer_reports_stop_assembly_and_load_line_summaries(self):
        records = [
            fake_record(
                "RATECON_001",
                stop_summary={
                    "stop_evidence_count": 4,
                    "stop_evidence_by_role": {"pickup": 2, "delivery": 2},
                    "stop_evidence_by_type": {"date": 2, "facility": 2},
                    "assembled_pickup_stop_candidate_count": 1,
                    "assembled_delivery_stop_candidate_count": 1,
                    "docs_with_assembled_pickup_stops": 1,
                    "docs_with_assembled_delivery_stops": 1,
                    "partial_stop_candidate_count": 0,
                    "ambiguous_stop_candidate_count": 1,
                },
                load_line_summary={
                    "lines_scanned": 10,
                    "label_hits": 2,
                    "emitted_candidates": 1,
                    "skipped_by_reason": {"candidate_looks_like_date": 1},
                    "emitted_by_method": {"adjacent_previous": 1},
                },
            )
        ]

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertEqual(analysis["stop_assembly_summary"]["stop_evidence_count"], 4)
        self.assertEqual(
            analysis["stop_assembly_summary"][
                "assembled_delivery_stop_candidate_count"
            ],
            1,
        )
        self.assertEqual(
            analysis["load_identity_line_summary"]["skipped_by_reason"][
                "candidate_looks_like_date"
            ],
            1,
        )
        self.assertEqual(
            analysis["load_identity_line_summary"]["emitted_by_method"][
                "adjacent_previous"
            ],
            1,
        )

    def test_analyzer_reports_layout_provider_and_pairing_summaries(self):
        records = [
            fake_record(
                "RATECON_001",
                layout_provider_summary={
                    "provider_requested": "pdfplumber",
                    "provider_used": "pdfplumber",
                    "available": True,
                    "status": "success",
                    "pages_with_words": 1,
                    "pages_with_lines": 1,
                    "pages_with_tables": 1,
                    "word_count": 20,
                    "line_count": 5,
                    "table_count": 1,
                    "table_cell_count": 6,
                    "warnings": [],
                    "errors": [],
                },
                table_summary={
                    "docs_with_tables": 1,
                    "tables_detected": 1,
                    "tables_with_stop_like_headers": 1,
                    "tables_with_rate_like_headers": 0,
                    "tables_with_load_like_headers": 1,
                    "recognized_stop_tables": 1,
                    "recognized_load_tables": 1,
                    "recognized_rate_tables": 0,
                    "unrecognized_tables": 0,
                    "table_header_role_counts": {
                        "load_identity": 1,
                        "stop_role": 1,
                    },
                    "table_row_role_counts": {"stop_role": 2},
                    "table_rows_with_stop_role": 2,
                    "table_rows_with_date_time_location": 1,
                },
                layout_load_summary={
                    "layout_label_hits": 2,
                    "same_row_pairings": 1,
                    "nearby_row_pairings": 0,
                    "table_cell_pairings": 1,
                    "header_block_pairings": 0,
                    "layout_candidates_emitted": 2,
                    "table_load_label_hits": 1,
                    "table_pairings_by_method": {
                        "table_key_value_row": 1,
                    },
                    "layout_rejection_reason_counts": {
                        "LAYOUT_LOAD_LABEL_NO_RIGHT_VALUE": 1
                    },
                },
                layout_stop_summary={
                    "layout_stop_evidence_count": 4,
                    "layout_structured_stop_candidates": 2,
                    "table_row_stop_candidates": 2,
                    "bbox_cluster_stop_candidates": 0,
                    "table_stop_candidates_complete": 1,
                    "table_stop_candidates_partial": 1,
                    "table_pairings_by_method": {
                        "table_row_semantic": 2,
                    },
                    "layout_ambiguity_reason_counts": {
                        "LAYOUT_STOP_ROLE_AMBIGUOUS": 1
                    },
                },
            )
        ]

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertEqual(analysis["layout_provider_summary"]["word_count"], 20)
        self.assertEqual(analysis["layout_provider_summary"]["table_count"], 1)
        self.assertEqual(analysis["table_extraction_summary"]["tables_detected"], 1)
        self.assertEqual(analysis["table_profile_summary"]["recognized_load_tables"], 1)
        self.assertEqual(
            analysis["table_profile_summary"]["table_header_role_counts"][
                "load_identity"
            ],
            1,
        )
        self.assertEqual(
            analysis["layout_load_pairing_summary"]["layout_candidates_emitted"],
            2,
        )
        self.assertEqual(
            analysis["layout_load_pairing_summary"]["table_pairings_by_method"][
                "table_key_value_row"
            ],
            1,
        )
        self.assertEqual(
            analysis["layout_stop_pairing_summary"]["table_row_stop_candidates"],
            2,
        )
        self.assertEqual(
            analysis["layout_stop_pairing_summary"]["table_stop_candidates_complete"],
            1,
        )

    def test_analyzer_reports_candidate_quality_summary(self):
        records = [
            fake_record(
                "RATECON_001",
                candidates={FIELD_LOAD_NUMBER: 1},
            )
        ]
        records[0]["candidate_summary"]["candidate_quality_summary"] = {
            "duplicate_candidates_removed": 2,
            "critical_fields_with_high_quality_independent_candidates": {
                FIELD_LOAD_NUMBER: 1
            },
            "critical_fields_with_only_weak_candidates": {"pickup_stops": 1},
            "critical_fields_with_only_legacy_fallback": {},
        }

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertEqual(
            analysis["candidate_quality_summary"]["duplicate_candidates_removed"],
            2,
        )
        self.assertEqual(
            analysis["candidate_quality_summary"][
                "critical_fields_with_high_quality_independent_candidates"
            ][FIELD_LOAD_NUMBER],
            1,
        )

    def test_analyzer_reports_layout_candidate_effectiveness(self):
        records = [fake_record("RATECON_001", candidates={FIELD_LOAD_NUMBER: 1})]
        records[0]["candidate_summary"]["layout_candidate_effectiveness"] = {
            "layout_load_candidates": {
                "emitted": 2,
                "by_pairing_method": {"table_key_value_row": 1},
                "by_id_type_hint": {"load": 1},
                "by_confidence_band": {"high": 1, "medium": 1},
                "accepted_by_resolver": 1,
                "rejected_or_not_selected": 1,
                "not_selected_reasons": {"not_selected_by_resolver": 1},
            },
            "layout_stop_candidates": {
                "emitted": 2,
                "structured": 2,
                "partial": 1,
                "by_pairing_method": {"table_row_semantic": 2},
                "with_location": 2,
                "with_date": 1,
                "with_time": 0,
                "accepted_by_resolver": 0,
                "rejected_or_not_selected": 2,
                "ambiguity_reasons": {"partial_stop_candidate": 1},
            },
        }

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertEqual(
            analysis["layout_candidate_effectiveness"]["layout_load_candidates"][
                "emitted"
            ],
            2,
        )
        self.assertEqual(
            analysis["layout_candidate_effectiveness"]["layout_stop_candidates"][
                "with_location"
            ],
            2,
        )

    def test_analyzer_reports_resolver_selection_and_review_gate(self):
        records = [fake_record("RATECON_001", candidates={FIELD_LOAD_NUMBER: 2})]
        records[0]["candidate_summary"]["resolver_selection_summary"] = {
            "fields": {
                FIELD_LOAD_NUMBER: {
                    "candidate_count_seen": 2,
                    "eligible_count": 2,
                    "ineligible_count": 0,
                    "selected": True,
                    "selected_count": 1,
                    "high_quality_not_selected_count": 1,
                    "not_selected_reason_counts": {"lower_confidence": 1},
                }
            }
        }
        records[0]["candidate_summary"]["load_number_selection_summary"] = {
            "docs_with_any_load_candidates": 1,
            "docs_with_high_quality_independent_load_candidates": 1,
            "docs_with_selected_load_number": 1,
            "docs_with_load_candidates_but_no_selection": 0,
            "not_selected_reason_counts": {"lower_confidence": 1},
            "selected_source_counts": {"native_layout": 1},
            "selected_pairing_method_counts": {"table_key_value_row": 1},
        }
        records[0]["candidate_summary"]["stop_selection_summary"] = {
            "pickup": {
                "docs_with_any_candidates": 1,
                "docs_with_partial_structured_candidates": 1,
                "docs_with_candidates_but_no_selection": 1,
                "not_selected_reason_counts": {"partial_only": 1},
            },
            "delivery": {},
        }
        records[0]["candidate_summary"]["review_gate_trace_summary"] = {
            "needs_review_count": 1,
            "critical_field_status_counts": {"load_number:passed": 1},
            "review_reason_source_counts": {"low_confidence": 1},
        }
        records[0]["candidate_summary"]["structured_stop_resolution_summary"] = {
            "pickup": {
                "docs_with_structured_candidates": 1,
                "docs_selected_partial": 1,
                "duplicates_collapsed": 2,
                "partial_overlaps": 1,
            },
            "delivery": {},
        }
        records[0]["candidate_summary"]["structured_stop_conflict_summary"] = {
            FIELD_PICKUP_STOPS: {
                "candidate_count": 3,
                "normalized_candidate_count": 2,
                "duplicates_collapsed": 2,
                "true_conflict_count": 0,
                "partial_overlap_count": 1,
                "conflict_type_counts": {},
            },
            FIELD_DELIVERY_STOPS: {},
        }
        records[0]["candidate_summary"]["rate_review_sanity_summary"] = {
            "docs_with_rate_candidates": 1,
            "docs_with_selected_rate": 1,
            "docs_marked_rate_missing": 0,
            "docs_marked_rate_low_confidence": 1,
            "rate_review_mismatch_count": 0,
            "mismatch_reasons": {},
        }

        analysis = analyze_ratecon_shadow_audit(audit_records=records)

        self.assertEqual(
            analysis["resolver_selection_summary"]["fields"][FIELD_LOAD_NUMBER][
                "candidate_count_seen"
            ],
            2,
        )
        self.assertEqual(
            analysis["load_number_selection_summary"]["selected_source_counts"][
                "native_layout"
            ],
            1,
        )
        self.assertEqual(
            analysis["stop_selection_summary"]["pickup"][
                "docs_with_candidates_but_no_selection"
            ],
            1,
        )
        self.assertEqual(
            analysis["review_gate_trace_summary"]["critical_field_status_counts"][
                "load_number:passed"
            ],
            1,
        )
        self.assertEqual(
            analysis["structured_stop_resolution_summary"]["pickup"][
                "docs_selected_partial"
            ],
            1,
        )
        self.assertEqual(
            analysis["structured_stop_conflict_summary"][FIELD_PICKUP_STOPS][
                "duplicates_collapsed"
            ],
            2,
        )
        self.assertEqual(
            analysis["rate_review_sanity_summary"]["docs_with_selected_rate"],
            1,
        )

    def test_analyzer_reports_baseline_deltas(self):
        baseline = analyze_ratecon_shadow_audit(
            audit_records=[
                fake_record("RATECON_001", candidates={}),
                fake_record("RATECON_002", candidates={}),
            ]
        )
        current = analyze_ratecon_shadow_audit(
            audit_records=[
                fake_record("RATECON_001", candidates={FIELD_LOAD_NUMBER: 1}),
                fake_record("RATECON_002", candidates={}),
            ],
            baseline_analysis=baseline,
        )

        self.assertEqual(
            current["baseline_deltas"]["candidate_missing_by_field"][FIELD_LOAD_NUMBER][
                "before_missing"
            ],
            2,
        )
        self.assertEqual(
            current["baseline_deltas"]["candidate_missing_by_field"][FIELD_LOAD_NUMBER][
                "after_missing"
            ],
            1,
        )


if __name__ == "__main__":
    unittest.main()
