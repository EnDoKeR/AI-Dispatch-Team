import tempfile
import unittest

from app.document_ai.document_extraction_artifact import (
    artifact_summary,
    extract_document_artifact_from_pdf,
)
from app.document_ai.field_candidate_provenance import (
    adapt_legacy_parser_output_to_field_candidates,
    build_field_candidate,
)
from app.document_ai.field_candidate_resolver import (
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
    FIELD_TOTAL_CARRIER_RATE,
    LOAD_RANKING_PROFILE_HEADER_RECALL_TABLE_SAFETY_V1,
    LOAD_RANKING_PROFILES,
    RATE_RANKING_PROFILES,
    RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
    RANKING_PROFILE_BASELINE,
    RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
    REVIEW_CONFLICTING_CANDIDATES,
    REVIEW_LOW_CONFIDENCE_CRITICAL_FIELD,
    REVIEW_MISSING_CRITICAL_FIELD,
    REVIEW_STRUCTURED_STOP_PARTIAL,
    build_resolver_decision_traces,
    resolve_candidates,
)
from app.document_ai.pdf_triage import triage_document
from app.document_ai.ratecon_document_pipeline import extract_ratecon_document
from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import (
    write_fake_empty_text_pdf,
    write_fake_text_pdf,
)


class RateConArchitectureSliceTests(unittest.TestCase):
    def test_triage_exposes_document_routing_fields_for_text_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir)
            result = triage_document(path, document_id="DOC-TRIAGE")

        self.assertEqual(result["document_id"], "DOC-TRIAGE")
        self.assertEqual(result["pdf_type"], "born_digital")
        self.assertTrue(result["native_text_available"])
        self.assertGreater(result["native_text_token_count"], 0)
        self.assertEqual(result["routing_decision"], "native_layout")
        self.assertTrue(result["layout_extraction_required"])
        self.assertFalse(result["ocr_required"])
        self.assertTrue(result["file_hash"])

    def test_triage_flags_empty_low_text_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_empty_text_pdf(temp_dir)
            result = triage_document(path)

        self.assertEqual(result["routing_decision"], "ocr")
        self.assertTrue(result["ocr_required"])
        self.assertIn("EMPTY_OR_LOW_TEXT", result["quality_flags"])
        self.assertIn("OCR_REQUIRED", result["quality_flags"])

    def test_document_artifact_preserves_plain_text_and_page_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir)
            artifact = extract_document_artifact_from_pdf(path, document_id="DOC-ART")

        summary = artifact_summary(artifact)
        self.assertEqual(artifact["document_id"], "DOC-ART")
        self.assertTrue(artifact["full_text"])
        self.assertEqual(summary["page_count"], 1)
        self.assertGreaterEqual(summary["line_count"], 1)
        self.assertIn("triage", artifact)

    def test_legacy_parser_output_adapts_to_provenance_candidates(self):
        parser_output = {
            "load_number": "FAKE-LOAD-001",
            "rate": "2500.00",
            "field_confidence": {"load_number": "HIGH", "rate": "MEDIUM"},
        }
        candidates = adapt_legacy_parser_output_to_field_candidates(
            parser_output,
            full_text="Load Number: FAKE-LOAD-001\nTotal Rate: 2500.00",
        )

        fields = {candidate["field"] for candidate in candidates}
        self.assertIn("load_number", fields)
        self.assertIn("total_carrier_rate", fields)
        self.assertTrue(all(candidate["evidence_text"] for candidate in candidates))
        self.assertTrue(all(candidate["parser_name"] for candidate in candidates))

    def test_resolver_prefers_load_label_over_po_label(self):
        candidates = [
            build_field_candidate(
                field="load_number",
                value="FAKE-PO-001",
                label="PO #",
                evidence_text="PO # FAKE-PO-001",
                source="native_text",
                confidence=0.9,
            ),
            build_field_candidate(
                field="load_number",
                value="FAKE-LOAD-002",
                label="Load #",
                evidence_text="Load # FAKE-LOAD-002",
                source="native_text",
                confidence=0.8,
            ),
        ]

        result = resolve_candidates(candidates, field_names=[FIELD_LOAD_NUMBER])

        self.assertEqual(result["resolved_fields"][FIELD_LOAD_NUMBER]["value"], "FAKE-LOAD-002")
        self.assertFalse(result["resolved_fields"][FIELD_LOAD_NUMBER]["needs_review"])

    def test_resolver_prefers_total_rate_over_accessorial_money(self):
        candidates = [
            build_field_candidate(
                field="total_carrier_rate",
                value="150.00",
                label="Detention",
                evidence_text="Detention: 150.00",
                source="native_text",
                confidence=0.95,
            ),
            build_field_candidate(
                field="total_carrier_rate",
                value="2500.00",
                label="Total Carrier Pay",
                evidence_text="Total Carrier Pay: 2500.00",
                source="native_text",
                confidence=0.8,
            ),
        ]

        result = resolve_candidates(candidates, field_names=[FIELD_TOTAL_CARRIER_RATE])

        self.assertEqual(
            result["resolved_fields"][FIELD_TOTAL_CARRIER_RATE]["value"],
            "2500.00",
        )

    def test_gold_diagnostic_profile_is_not_default_for_header_reference_ids(self):
        candidates = [
            {
                "field": "reference_numbers",
                "value": "PO-PRIMARY",
                "normalized_value": "PO-PRIMARY",
                "label": "PO #",
                "evidence_text": "rate confirmation header id present",
                "source": "native_layout",
                "parser_name": "layout_load_identity_pairing_generator",
                "confidence": 0.82,
                "metadata": {
                    "id_type_hint": "po",
                    "document_region": "load_info",
                    "is_document_title_or_header_id": True,
                    "context_feature_load_identity_candidate": True,
                    "pairing_method": "same_row_right",
                },
            }
        ]

        baseline = resolve_candidates(candidates, field_names=[FIELD_LOAD_NUMBER])
        experiment = resolve_candidates(
            candidates,
            field_names=[FIELD_LOAD_NUMBER],
            ranking_profile=RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
        )

        self.assertEqual(baseline["resolved_fields"][FIELD_LOAD_NUMBER]["value"], "")
        self.assertEqual(
            experiment["resolved_fields"][FIELD_LOAD_NUMBER]["value"],
            "PO-PRIMARY",
        )

    def test_gold_diagnostic_profile_penalizes_stop_level_load_reference(self):
        candidates = [
            {
                "field": "load_number",
                "value": "PU-REF-1",
                "normalized_value": "PU-REF-1",
                "label": "Pickup #",
                "evidence_text": "pickup section reference present",
                "source": "native_layout",
                "parser_name": "layout_load_identity_pairing_generator",
                "confidence": 0.92,
                "metadata": {
                    "id_type_hint": "pickup_ref",
                    "document_region": "stop_section",
                    "is_pickup_delivery_reference": True,
                    "is_stop_level_reference": True,
                    "pairing_method": "table_key_value_row",
                },
            },
            {
                "field": "reference_numbers",
                "value": "PO-PRIMARY",
                "normalized_value": "PO-PRIMARY",
                "label": "PO #",
                "evidence_text": "rate confirmation header id present",
                "source": "native_layout",
                "parser_name": "layout_load_identity_pairing_generator",
                "confidence": 0.76,
                "metadata": {
                    "id_type_hint": "po",
                    "document_region": "load_info",
                    "is_document_title_or_header_id": True,
                    "context_feature_load_identity_candidate": True,
                    "pairing_method": "same_row_right",
                },
            },
        ]

        baseline = resolve_candidates(candidates, field_names=[FIELD_LOAD_NUMBER])
        experiment = resolve_candidates(
            candidates,
            field_names=[FIELD_LOAD_NUMBER],
            ranking_profile=RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
        )

        self.assertEqual(baseline["resolved_fields"][FIELD_LOAD_NUMBER]["value"], "PU-REF-1")
        self.assertEqual(
            experiment["resolved_fields"][FIELD_LOAD_NUMBER]["value"],
            "PO-PRIMARY",
        )
        selected = experiment["resolved_fields"][FIELD_LOAD_NUMBER]["selected_candidate"]
        self.assertEqual(
            selected["metadata"]["ranking_profile"],
            RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
        )

    def test_gold_diagnostic_profile_penalizes_line_item_rate_against_total_cost(self):
        candidates = [
            {
                "field": "total_carrier_rate",
                "value": "1500.00",
                "normalized_value": "1500.00",
                "label": "Linehaul",
                "evidence_text": "Linehaul 1500.00",
                "source": "native_layout",
                "parser_name": "layout_rate_candidate_generator",
                "confidence": 0.86,
                "metadata": {
                    "money_context": "line_item_rate",
                    "is_line_item_only": True,
                },
            },
            {
                "field": "total_carrier_rate",
                "value": "1800.00",
                "normalized_value": "1800.00",
                "label": "Total Cost",
                "evidence_text": "Total Cost 1800.00",
                "source": "native_layout",
                "parser_name": "layout_rate_candidate_generator",
                "confidence": 0.65,
                "metadata": {
                    "money_context": "total_rate",
                    "is_total_pay_candidate": True,
                },
            },
        ]

        baseline = resolve_candidates(candidates, field_names=[FIELD_TOTAL_CARRIER_RATE])
        experiment = resolve_candidates(
            candidates,
            field_names=[FIELD_TOTAL_CARRIER_RATE],
            ranking_profile=RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
        )

        self.assertEqual(
            baseline["resolved_fields"][FIELD_TOTAL_CARRIER_RATE]["value"],
            "1500.00",
        )
        self.assertEqual(
            experiment["resolved_fields"][FIELD_TOTAL_CARRIER_RATE]["value"],
            "1800.00",
        )

    def test_field_scoped_rate_profile_does_not_affect_load_number(self):
        candidates = [
            {
                "field": "reference_numbers",
                "value": "PO-PRIMARY",
                "normalized_value": "PO-PRIMARY",
                "label": "PO #",
                "evidence_text": "rate confirmation header id present",
                "source": "native_layout",
                "parser_name": "layout_load_identity_pairing_generator",
                "confidence": 0.82,
                "metadata": {
                    "id_type_hint": "po",
                    "document_region": "load_info",
                    "is_document_title_or_header_id": True,
                    "context_feature_load_identity_candidate": True,
                    "pairing_method": "same_row_right",
                },
            }
        ]

        broad = resolve_candidates(
            candidates,
            field_names=[FIELD_LOAD_NUMBER],
            ranking_profile=RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
        )
        field_scoped_rate = resolve_candidates(
            candidates,
            field_names=[FIELD_LOAD_NUMBER],
            ranking_profile=RANKING_PROFILE_BASELINE,
            rate_ranking_profile=RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
        )

        self.assertEqual(broad["resolved_fields"][FIELD_LOAD_NUMBER]["value"], "PO-PRIMARY")
        self.assertEqual(field_scoped_rate["resolved_fields"][FIELD_LOAD_NUMBER]["value"], "")
        self.assertEqual(
            field_scoped_rate["field_ranking_profiles"][FIELD_LOAD_NUMBER],
            RANKING_PROFILE_BASELINE,
        )
        self.assertEqual(
            field_scoped_rate["rate_ranking_profile"],
            RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
        )

    def test_field_scoped_load_profile_does_not_affect_rate_selection(self):
        candidates = [
            {
                "field": "total_carrier_rate",
                "value": "1500.00",
                "normalized_value": "1500.00",
                "label": "Linehaul",
                "evidence_text": "Linehaul 1500.00",
                "source": "native_layout",
                "parser_name": "layout_rate_candidate_generator",
                "confidence": 0.86,
                "metadata": {
                    "money_context": "line_item_rate",
                    "is_line_item_only": True,
                },
            },
            {
                "field": "total_carrier_rate",
                "value": "1800.00",
                "normalized_value": "1800.00",
                "label": "Total Cost",
                "evidence_text": "Total Cost 1800.00",
                "source": "native_layout",
                "parser_name": "layout_rate_candidate_generator",
                "confidence": 0.65,
                "metadata": {
                    "money_context": "total_rate",
                    "is_total_pay_candidate": True,
                },
            },
        ]

        load_only = resolve_candidates(
            candidates,
            field_names=[FIELD_TOTAL_CARRIER_RATE],
            load_ranking_profile=LOAD_RANKING_PROFILE_HEADER_RECALL_TABLE_SAFETY_V1,
        )
        rate_only = resolve_candidates(
            candidates,
            field_names=[FIELD_TOTAL_CARRIER_RATE],
            rate_ranking_profile=RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
        )

        self.assertEqual(
            load_only["resolved_fields"][FIELD_TOTAL_CARRIER_RATE]["value"],
            "1500.00",
        )
        self.assertEqual(
            rate_only["resolved_fields"][FIELD_TOTAL_CARRIER_RATE]["value"],
            "1800.00",
        )
        self.assertEqual(
            load_only["field_ranking_profiles"][FIELD_TOTAL_CARRIER_RATE],
            RANKING_PROFILE_BASELINE,
        )
        self.assertIn(RANKING_PROFILE_GOLD_DIAGNOSTIC_V1, RATE_RANKING_PROFILES)
        self.assertIn(RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1, RATE_RANKING_PROFILES)
        self.assertIn("header_recall_table_abstain_v1", LOAD_RANKING_PROFILES)

    def test_money_abstain_profile_does_not_affect_load_number(self):
        candidates = [
            {
                "field": "reference_numbers",
                "value": "PO-PRIMARY",
                "normalized_value": "PO-PRIMARY",
                "label": "PO #",
                "evidence_text": "rate confirmation header id present",
                "source": "native_layout",
                "parser_name": "layout_load_identity_pairing_generator",
                "confidence": 0.82,
                "metadata": {
                    "id_type_hint": "po",
                    "document_region": "load_info",
                    "is_document_title_or_header_id": True,
                    "context_feature_load_identity_candidate": True,
                    "pairing_method": "same_row_right",
                },
            }
        ]

        result = resolve_candidates(
            candidates,
            field_names=[FIELD_LOAD_NUMBER],
            rate_ranking_profile=RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
        )

        self.assertEqual(result["resolved_fields"][FIELD_LOAD_NUMBER]["value"], "")
        self.assertEqual(
            result["field_ranking_profiles"][FIELD_LOAD_NUMBER],
            RANKING_PROFILE_BASELINE,
        )

    def test_money_abstain_profile_demotes_per_unit_and_selects_total(self):
        candidates = [
            {
                "field": "total_carrier_rate",
                "value": "2.50",
                "normalized_value": "2.50",
                "label": "Rate per mile",
                "evidence_text": "Rate per mile 2.50",
                "source": "native_layout",
                "parser_name": "layout_rate_candidate_generator",
                "confidence": 0.98,
                "metadata": {"money_context": "per_unit_rate", "is_per_unit_rate": True},
            },
            {
                "field": "total_carrier_rate",
                "value": "2500.00",
                "normalized_value": "2500.00",
                "label": "Total Carrier Pay",
                "evidence_text": "Total Carrier Pay 2500.00",
                "source": "native_layout",
                "parser_name": "layout_rate_candidate_generator",
                "confidence": 0.76,
                "metadata": {"money_context": "total_carrier_pay"},
            },
        ]

        result = resolve_candidates(
            candidates,
            field_names=[FIELD_TOTAL_CARRIER_RATE],
            rate_ranking_profile=RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
        )

        rate = result["resolved_fields"][FIELD_TOTAL_CARRIER_RATE]
        self.assertEqual(rate["value"], "2500.00")
        self.assertEqual(rate["selected_candidate"]["metadata"]["rate_safety"], "safe")

    def test_money_abstain_profile_turns_only_unsafe_rate_into_missing_review(self):
        candidates = [
            {
                "field": "total_carrier_rate",
                "value": "150.00",
                "normalized_value": "150.00",
                "label": "QuickPay Fee",
                "evidence_text": "QuickPay Fee 150.00",
                "source": "native_layout",
                "parser_name": "layout_rate_candidate_generator",
                "confidence": 0.96,
                "metadata": {"money_context": "quickpay"},
            }
        ]

        result = resolve_candidates(
            candidates,
            field_names=[FIELD_TOTAL_CARRIER_RATE],
            rate_ranking_profile=RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
        )

        rate = result["resolved_fields"][FIELD_TOTAL_CARRIER_RATE]
        self.assertEqual(rate["value"], "")
        self.assertIn(REVIEW_MISSING_CRITICAL_FIELD, rate["review_reasons"])

    def test_gold_diagnostic_profile_keeps_conflicting_totals_review_required(self):
        candidates = [
            {
                "field": "total_carrier_rate",
                "value": "1800.00",
                "normalized_value": "1800.00",
                "label": "Total Carrier Pay",
                "evidence_text": "Total Carrier Pay 1800.00",
                "source": "native_layout",
                "confidence": 0.86,
                "metadata": {"money_context": "total_carrier_pay"},
            },
            {
                "field": "total_carrier_rate",
                "value": "1900.00",
                "normalized_value": "1900.00",
                "label": "Agreed Rate Total",
                "evidence_text": "Agreed Rate Total 1900.00",
                "source": "native_layout",
                "confidence": 0.86,
                "metadata": {"money_context": "total_rate"},
            },
        ]

        result = resolve_candidates(
            candidates,
            field_names=[FIELD_TOTAL_CARRIER_RATE],
            ranking_profile=RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
        )

        rate = result["resolved_fields"][FIELD_TOTAL_CARRIER_RATE]
        self.assertTrue(rate["needs_review"])
        self.assertEqual(rate["value"], "")

    def test_resolver_routes_conflicting_strong_rates_to_review(self):
        candidates = [
            build_field_candidate(
                field="total_carrier_rate",
                value="2500.00",
                label="Total Carrier Pay",
                evidence_text="Total Carrier Pay: 2500.00",
                source="native_text",
                confidence=0.9,
            ),
            build_field_candidate(
                field="total_carrier_rate",
                value="2800.00",
                label="Agreed Amount",
                evidence_text="Agreed Amount: 2800.00",
                source="native_layout",
                confidence=0.9,
            ),
        ]

        result = resolve_candidates(candidates, field_names=[FIELD_TOTAL_CARRIER_RATE])
        rate = result["resolved_fields"][FIELD_TOTAL_CARRIER_RATE]

        self.assertTrue(rate["needs_review"])
        self.assertEqual(rate["value"], "")
        self.assertIn(
            f"{REVIEW_CONFLICTING_CANDIDATES}:{FIELD_TOTAL_CARRIER_RATE}",
            result["review_reasons"],
        )
        self.assertEqual(
            result["review_gate_trace"]["critical_field_status"][FIELD_TOTAL_CARRIER_RATE][
                "status"
            ],
            "conflict",
        )

    def test_review_gate_flags_missing_and_low_confidence_critical_fields(self):
        candidates = [
            build_field_candidate(
                field="load_number",
                value="FAKE-LOAD-LOW",
                label="Load #",
                evidence_text="Load # FAKE-LOAD-LOW",
                confidence=0.2,
            )
        ]

        result = resolve_candidates(
            candidates,
            field_names=[FIELD_LOAD_NUMBER, FIELD_TOTAL_CARRIER_RATE],
        )

        self.assertTrue(result["needs_review"])
        self.assertIn(
            f"{REVIEW_LOW_CONFIDENCE_CRITICAL_FIELD}:{FIELD_LOAD_NUMBER}",
            result["review_reasons"],
        )
        self.assertIn(
            f"{REVIEW_MISSING_CRITICAL_FIELD}:{FIELD_TOTAL_CARRIER_RATE}",
            result["review_reasons"],
        )
        self.assertIn("review_gate_trace", result)
        self.assertEqual(
            result["review_gate_trace"]["critical_field_status"][FIELD_TOTAL_CARRIER_RATE]["status"],
            "missing",
        )

    def test_resolver_decision_trace_redacts_values_and_counts_rejections(self):
        candidates = [
            build_field_candidate(
                field="load_number",
                value="FAKE-LOAD-001",
                label="Load #",
                evidence_text="Load # FAKE-LOAD-001",
                source="native_layout",
                parser_name="layout_load_identity_pairing_generator",
                confidence=0.86,
                metadata={"pairing_method": "table_key_value_row"},
            ),
            build_field_candidate(
                field="load_number",
                value="FAKE-PO-002",
                label="PO #",
                evidence_text="PO # FAKE-PO-002",
                source="native_layout",
                parser_name="layout_load_identity_pairing_generator",
                confidence=0.70,
                metadata={"canonical_mapping_strength": "weak"},
            ),
        ]

        result = resolve_candidates(candidates, field_names=[FIELD_LOAD_NUMBER])
        trace = result["resolver_decision_traces"][FIELD_LOAD_NUMBER]
        payload = str(trace)

        self.assertEqual(trace["decision_status"], "selected")
        self.assertEqual(trace["candidate_count_seen"], 2)
        self.assertEqual(trace["candidate_count_eligible"], 2)
        self.assertEqual(trace["selected_candidate"]["quality_band"], "high")
        self.assertNotIn("FAKE-LOAD-001", payload)
        self.assertTrue(trace["top_rejected_or_not_selected"])

    def test_candidate_eligibility_marks_structured_stop_candidate(self):
        candidates = [
            {
                "field": FIELD_PICKUP_STOPS,
                "value": [{"role": "pickup"}],
                "normalized_value": "pickup_stop_assembled",
                "label": "pickup_stop_assembled",
                "evidence_text": "pickup_stop evidence",
                "source": "native_layout",
                "parser_name": "layout_stop_table_candidate_generator",
                "confidence": 0.78,
                "metadata": {
                    "structured_stop_candidate": True,
                    "has_location": True,
                    "has_date": True,
                    "pairing_method": "table_row_semantic",
                },
            }
        ]

        traces = build_resolver_decision_traces(
            candidates,
            resolved_fields={
                FIELD_PICKUP_STOPS: {
                    "value": "pickup_stop_assembled",
                    "confidence": 0.78,
                    "selected_candidate": {
                        "value": "pickup_stop_assembled",
                        "normalized_value": "pickup_stop_assembled",
                        "parser_name": "layout_stop_table_candidate_generator",
                        "source": "native_layout",
                        "label": "pickup_stop_assembled",
                    },
                }
            },
            field_names=[FIELD_PICKUP_STOPS],
        )

        trace = traces[FIELD_PICKUP_STOPS]
        self.assertEqual(trace["candidate_count_eligible"], 1)
        self.assertEqual(trace["selected_candidate"]["value_shape"]["list"], True)
        self.assertTrue(
            trace["selected_candidate"]["metadata_summary"]["structured_stop_candidate"]
        )

    def test_structured_complete_pickup_stop_is_selected(self):
        candidates = [
            {
                "field": FIELD_PICKUP_STOPS,
                "value": [
                    {
                        "role": "pickup",
                        "facility": "Fake Facility",
                        "date": "01/02/2030",
                        "time": "08:00",
                    }
                ],
                "normalized_value": "pickup_stop_assembled",
                "label": "pickup_stop",
                "evidence_text": "pickup_stop: structured evidence present",
                "source": "native_layout",
                "parser_name": "layout_stop_table_candidate_generator",
                "confidence": 0.78,
                "metadata": {
                    "structured_stop_candidate": True,
                    "stop_role": "pickup",
                    "has_location": True,
                    "has_date": True,
                    "has_time": True,
                    "pairing_method": "table_row_semantic",
                },
            }
        ]

        result = resolve_candidates(candidates, field_names=[FIELD_PICKUP_STOPS])
        stop = result["resolved_fields"][FIELD_PICKUP_STOPS]

        self.assertEqual(stop["structure_status"], "complete")
        self.assertEqual(stop["selected_status"], "selected_complete")
        self.assertFalse(stop["needs_review"])
        self.assertEqual(
            result["review_gate_trace"]["critical_field_status"][FIELD_PICKUP_STOPS]["status"],
            "passed",
        )

    def test_structured_partial_pickup_stop_is_present_but_review_required(self):
        candidates = [
            {
                "field": FIELD_PICKUP_STOPS,
                "value": [{"role": "pickup", "city": "Fake City"}],
                "normalized_value": "pickup_stop_assembled",
                "label": "pickup_stop",
                "evidence_text": "pickup_stop: location evidence present",
                "source": "native_layout",
                "parser_name": "layout_stop_table_candidate_generator",
                "confidence": 0.62,
                "metadata": {
                    "structured_stop_candidate": True,
                    "stop_role": "pickup",
                    "has_location": True,
                    "has_date": False,
                    "pairing_method": "table_row_semantic",
                },
            }
        ]

        result = resolve_candidates(candidates, field_names=[FIELD_PICKUP_STOPS])
        stop = result["resolved_fields"][FIELD_PICKUP_STOPS]
        gate = result["review_gate_trace"]["critical_field_status"][FIELD_PICKUP_STOPS]

        self.assertEqual(stop["structure_status"], "useful_partial")
        self.assertIn(REVIEW_STRUCTURED_STOP_PARTIAL, stop["review_reasons"])
        self.assertEqual(gate["status"], "partial_review_required")
        self.assertTrue(result["needs_review"])

    def test_structured_stop_duplicate_is_collapsed_not_conflict(self):
        candidates = [
            {
                "field": FIELD_PICKUP_STOPS,
                "value": [{"role": "pickup", "city": "Fake City", "date": "01/02/2030"}],
                "normalized_value": "pickup_stop_a",
                "label": "pickup_stop",
                "source": "native_layout",
                "parser_name": "layout_stop_table_candidate_generator",
                "confidence": 0.78,
                "metadata": {"structured_stop_candidate": True, "stop_role": "pickup"},
            },
            {
                "field": FIELD_PICKUP_STOPS,
                "value": [{"role": "pickup", "city": "Fake City", "date": "01/02/2030"}],
                "normalized_value": "pickup_stop_b",
                "label": "pickup_stop",
                "source": "native_layout",
                "parser_name": "stop_evidence_assembler",
                "confidence": 0.75,
                "metadata": {"structured_stop_candidate": True, "stop_role": "pickup"},
            },
        ]

        result = resolve_candidates(candidates, field_names=[FIELD_PICKUP_STOPS])
        summary = result["resolved_fields"][FIELD_PICKUP_STOPS][
            "structured_stop_conflict_summary"
        ]

        self.assertEqual(summary["duplicates_collapsed"], 1)
        self.assertEqual(summary["true_conflict_count"], 0)
        self.assertNotIn(
            f"{REVIEW_CONFLICTING_CANDIDATES}:{FIELD_PICKUP_STOPS}",
            result["review_reasons"],
        )

    def test_structured_stop_true_date_conflict_remains_review_required(self):
        candidates = [
            {
                "field": FIELD_PICKUP_STOPS,
                "value": [{"role": "pickup", "city": "Fake City", "date": "01/02/2030"}],
                "normalized_value": "pickup_stop_a",
                "label": "pickup_stop",
                "source": "native_layout",
                "parser_name": "layout_stop_table_candidate_generator",
                "confidence": 0.82,
                "metadata": {"structured_stop_candidate": True, "stop_role": "pickup"},
            },
            {
                "field": FIELD_PICKUP_STOPS,
                "value": [{"role": "pickup", "city": "Fake City", "date": "01/03/2030"}],
                "normalized_value": "pickup_stop_b",
                "label": "pickup_stop",
                "source": "native_layout",
                "parser_name": "stop_evidence_assembler",
                "confidence": 0.82,
                "metadata": {"structured_stop_candidate": True, "stop_role": "pickup"},
            },
        ]

        result = resolve_candidates(candidates, field_names=[FIELD_PICKUP_STOPS])
        stop = result["resolved_fields"][FIELD_PICKUP_STOPS]

        self.assertEqual(stop["selected_status"], "conflict")
        self.assertIn(REVIEW_CONFLICTING_CANDIDATES, stop["review_reasons"])
        self.assertEqual(
            result["review_gate_trace"]["critical_field_status"][FIELD_PICKUP_STOPS]["status"],
            "conflict_review_required",
        )

    def test_legacy_fallback_does_not_beat_complete_layout_stop(self):
        candidates = [
            {
                "field": FIELD_PICKUP_STOPS,
                "value": "1",
                "normalized_value": "1",
                "label": "pickup_count",
                "source": "legacy_final_output",
                "parser_name": "legacy_final_output_adapter",
                "confidence": 0.55,
                "metadata": {
                    "diagnostic_fallback": True,
                    "not_independent_candidate": True,
                    "stop_role": "pickup",
                    "stop_count": 1,
                },
            },
            {
                "field": FIELD_PICKUP_STOPS,
                "value": [{"role": "pickup", "city": "Fake City", "date": "01/02/2030"}],
                "normalized_value": "pickup_stop",
                "label": "pickup_stop",
                "source": "native_layout",
                "parser_name": "layout_stop_table_candidate_generator",
                "confidence": 0.78,
                "metadata": {"structured_stop_candidate": True, "stop_role": "pickup"},
            },
        ]

        result = resolve_candidates(candidates, field_names=[FIELD_PICKUP_STOPS])
        selected = result["resolved_fields"][FIELD_PICKUP_STOPS]["selected_candidate"]

        self.assertEqual(selected["parser_name"], "layout_stop_table_candidate_generator")

    def test_document_pipeline_returns_backward_compatible_final_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fake_text_pdf(temp_dir)
            result = extract_ratecon_document(path, document_id="DOC-PIPE", include_debug=True)

        final_output = result["final_output"]
        self.assertIn("broker_name", final_output)
        self.assertIn("load_number", final_output)
        self.assertIn("rate", final_output)
        self.assertIn("needs_review", final_output)
        self.assertIn("review_reasons", final_output)
        self.assertIn("triage", result["debug"])
        self.assertIn("artifact_summary", result["debug"])
        self.assertIn("candidates", result["debug"])
        self.assertIn("resolver_decision_traces", result["debug"])
        self.assertIn("review_gate_trace", result["debug"])


if __name__ == "__main__":
    unittest.main()
