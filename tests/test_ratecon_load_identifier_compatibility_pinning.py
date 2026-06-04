import unittest

from app.document_ai import load_identifier_candidates as load_ids
from app.document_ai import load_identifier_coverage_audit as coverage
from app.document_ai import load_identifier_source_line_audit as source_line
from app.document_ai import load_identity_forensics as forensics
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    FIELD_LOAD_NUMBER,
    FIELD_REFERENCE,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_CONFLICT,
    FIELD_RESOLUTION_STATUS_MISSING,
    FIELD_RESOLUTION_STATUS_NEEDS_REVIEW,
    FIELD_RESOLUTION_STATUS_RESOLVED,
    resolve_ratecon_fields,
)
from tests.helpers.ratecon_selected_load_regression import run_selected_load_cases


class RateconLoadIdentifierCompatibilityPinningTests(unittest.TestCase):
    def test_candidate_taxonomy_values_are_pinned(self):
        self.assertEqual("broker_load_number", load_ids.LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER)
        self.assertEqual("order_number", load_ids.LOAD_IDENTIFIER_TYPE_ORDER_NUMBER)
        self.assertEqual("pro_number", load_ids.LOAD_IDENTIFIER_TYPE_PRO_NUMBER)
        self.assertEqual("po_number", load_ids.LOAD_IDENTIFIER_TYPE_PO_NUMBER)
        self.assertEqual("customer_reference", load_ids.LOAD_IDENTIFIER_TYPE_CUSTOMER_REFERENCE)
        self.assertIn("load #", load_ids.STRONG_PRIMARY_IDENTIFIER_LABELS)
        self.assertIn("po #", load_ids.NEGATIVE_PRIMARY_IDENTIFIER_LABELS)
        self.assertIn("reference #", load_ids.MEDIUM_CONTEXTUAL_IDENTIFIER_LABELS)

    def test_candidate_builder_shape_is_pinned(self):
        candidate = load_ids.build_load_identifier_candidate(
            candidate_id="fake-load-candidate",
            identifier_type=load_ids.LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
            raw_value="FAKE-LOAD-101",
            normalized_value="FAKE-LOAD-101",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            label="Load #",
        )

        self.assertEqual(FIELD_LOAD_NUMBER, candidate["field_name"])
        self.assertEqual("FAKE-LOAD-101", candidate["raw_value"])
        self.assertEqual("FAKE-LOAD-101", candidate["normalized_value"])
        self.assertEqual("broker_load_number", candidate["identifier_type"])
        self.assertTrue(candidate["primary_load_identifier_candidate"])
        self.assertEqual("label_pattern", candidate["source"])

    def test_non_primary_reference_shape_is_pinned(self):
        candidate = load_ids.build_load_identifier_candidate(
            identifier_type=load_ids.LOAD_IDENTIFIER_TYPE_PO_NUMBER,
            raw_value="FAKE-PO-101",
            normalized_value="FAKE-PO-101",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            label="PO #",
        )

        self.assertEqual(FIELD_REFERENCE, candidate["field_name"])
        self.assertEqual("po_number", candidate["identifier_type"])
        self.assertFalse(candidate["primary_load_identifier_candidate"])

    def test_label_classification_behavior_is_pinned(self):
        strong = load_ids.classify_identifier_label("Load #")
        generic = load_ids.classify_identifier_label(
            "Ref #",
            {"page_role": "header", "section_role": "load confirmation"},
        )
        stop_ref = load_ids.classify_identifier_label("Ref #", {"section_role": "pickup stop"})
        po = load_ids.classify_identifier_label("PO #")

        self.assertTrue(strong["primary_load_identifier_candidate"])
        self.assertEqual("broker_load_number", strong["identifier_type"])
        self.assertTrue(generic["primary_load_identifier_candidate"])
        self.assertEqual("primary_reference", generic["identifier_type"])
        self.assertFalse(stop_ref["primary_load_identifier_candidate"])
        self.assertIn("ambiguous_reference_label", stop_ref["warning_codes"])
        self.assertFalse(po["primary_load_identifier_candidate"])
        self.assertIn("not_primary_load_identifier", po["warning_codes"])

    def test_resolver_statuses_are_pinned(self):
        load_candidate = load_ids.build_load_identifier_candidate(
            identifier_type=load_ids.LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
            raw_value="FAKE-LOAD-102",
            normalized_value="FAKE-LOAD-102",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            label="Load #",
        )
        po_candidate = load_ids.build_load_identifier_candidate(
            identifier_type=load_ids.LOAD_IDENTIFIER_TYPE_PO_NUMBER,
            raw_value="FAKE-PO-102",
            normalized_value="FAKE-PO-102",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            label="PO #",
        )
        generic_candidate = load_ids.build_load_identifier_candidate(
            identifier_type=load_ids.LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
            raw_value="FAKE-REF-102",
            normalized_value="FAKE-REF-102",
            confidence="MEDIUM",
            label="Ref #",
            warnings=["generic_identifier_requires_review"],
        )
        conflict_candidate = load_ids.build_load_identifier_candidate(
            identifier_type=load_ids.LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
            raw_value="FAKE-ORDER-102",
            normalized_value="FAKE-ORDER-102",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            label="Order #",
        )

        resolved = resolve_ratecon_fields({"candidates": [load_candidate]}, field_names=[FIELD_LOAD_NUMBER])
        missing = resolve_ratecon_fields({"candidates": [po_candidate]}, field_names=[FIELD_LOAD_NUMBER])
        needs_review = resolve_ratecon_fields({"candidates": [generic_candidate]}, field_names=[FIELD_LOAD_NUMBER])
        conflict = resolve_ratecon_fields(
            {"candidates": [load_candidate, conflict_candidate]},
            field_names=[FIELD_LOAD_NUMBER],
        )

        self.assertEqual(FIELD_RESOLUTION_STATUS_RESOLVED, resolved["resolutions"][0]["status"])
        self.assertEqual(FIELD_RESOLUTION_STATUS_MISSING, missing["resolutions"][0]["status"])
        self.assertEqual(FIELD_RESOLUTION_STATUS_NEEDS_REVIEW, needs_review["resolutions"][0]["status"])
        self.assertEqual(FIELD_RESOLUTION_STATUS_CONFLICT, conflict["resolutions"][0]["status"])

    def test_forensics_and_audit_labels_are_pinned(self):
        self.assertEqual("load_number", forensics.normalized_label("Load #"))
        self.assertEqual("reference_number", forensics.normalized_label("PO #"))
        self.assertEqual("candidate_looks_like_money", forensics.identifier_value_rejection_reason("$1,500.00"))
        self.assertEqual("candidate_looks_like_date", forensics.identifier_value_rejection_reason("06/04/2026"))
        self.assertEqual("", forensics.identifier_value_rejection_reason("FAKE-LOAD-103"))
        self.assertEqual("load_number", coverage.LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER)
        self.assertEqual("core_load_number_mapped", coverage.LOAD_ID_AUDIT_STAGE_CORE_LOAD_NUMBER_MAPPED)
        self.assertEqual("load_number", source_line.LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER)
        self.assertEqual("core_mapped", source_line.LOAD_ID_SOURCE_STAGE_CORE_MAPPED)

    def test_selected_load_regression_outputs_are_pinned(self):
        results = run_selected_load_cases()
        by_id = {result["case_id"]: result for result in results}

        self.assertEqual("FAKE-LOAD-001", by_id["explicit_load_number_header"]["selected_value"])
        self.assertEqual("missing", by_id["po_number_not_load_when_current_behavior_rejects"]["status"])
        self.assertEqual("needs_review", by_id["broker_reference_only"]["status"])
        self.assertEqual("resolved", by_id["table_neighbor_wrong_cell_known_debt"]["status"])


if __name__ == "__main__":
    unittest.main()
