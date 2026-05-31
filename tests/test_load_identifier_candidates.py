import json
import unittest

from app.document_ai.load_identifier_candidates import (
    LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
    LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
    LOAD_IDENTIFIER_TYPE_PO_NUMBER,
    LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
    LOAD_IDENTIFIER_TYPE_TENDER_ID,
    build_load_identifier_candidate,
    classify_identifier_label,
    is_negative_primary_identifier_label,
    is_primary_load_identifier_label,
    is_primary_load_identifier_type,
    normalize_identifier_type,
    score_identifier_label,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    FIELD_LOAD_NUMBER,
    FIELD_REFERENCE,
    CANDIDATE_CONFIDENCE_MEDIUM,
)


class LoadIdentifierCandidateContractTests(unittest.TestCase):
    def test_create_broker_load_number_candidate(self):
        candidate = build_load_identifier_candidate(
            candidate_id="fake-load-id-1",
            identifier_type=LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
            raw_value="FAKE-LOAD-001",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            confidence_reasons=["strong_primary_identifier_label"],
            label="Load #",
        )

        self.assertEqual(candidate["field_name"], FIELD_LOAD_NUMBER)
        self.assertEqual(candidate["identifier_type"], LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER)
        self.assertTrue(candidate["primary_load_identifier_candidate"])

    def test_create_order_number_candidate(self):
        candidate = build_load_identifier_candidate(
            identifier_type=LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
            raw_value="FAKE-ORDER-002",
            label="Order #",
        )

        self.assertEqual(candidate["field_name"], FIELD_LOAD_NUMBER)
        self.assertEqual(candidate["identifier_type"], LOAD_IDENTIFIER_TYPE_ORDER_NUMBER)
        self.assertTrue(candidate["primary_load_identifier_candidate"])

    def test_create_po_candidate_that_is_not_primary(self):
        candidate = build_load_identifier_candidate(
            identifier_type=LOAD_IDENTIFIER_TYPE_PO_NUMBER,
            raw_value="FAKE-PO-003",
            label="PO #",
        )

        self.assertEqual(candidate["field_name"], FIELD_REFERENCE)
        self.assertEqual(candidate["identifier_type"], LOAD_IDENTIFIER_TYPE_PO_NUMBER)
        self.assertFalse(candidate["primary_load_identifier_candidate"])

    def test_serializes_candidate_without_private_value_requirement(self):
        candidate = build_load_identifier_candidate(
            identifier_type=LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
            label="Load #",
        )

        payload = json.dumps(candidate, sort_keys=True)
        self.assertIn("primary_load_identifier_candidate", payload)
        self.assertEqual(candidate["raw_value"], "")
        self.assertEqual(candidate["normalized_value"], "")

    def test_identifier_type_normalization(self):
        self.assertEqual(
            normalize_identifier_type("broker load number"),
            LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
        )
        self.assertTrue(is_primary_load_identifier_type("order-number"))
        self.assertFalse(is_primary_load_identifier_type("po number"))

    def test_load_number_label_is_strong_primary(self):
        classification = classify_identifier_label("Load #")

        self.assertEqual(
            classification["identifier_type"],
            LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
        )
        self.assertTrue(classification["primary_load_identifier_candidate"])
        self.assertEqual(classification["confidence"], CANDIDATE_CONFIDENCE_HIGH)

    def test_tender_id_label_is_strong_primary(self):
        classification = classify_identifier_label("Tender ID")

        self.assertEqual(classification["identifier_type"], LOAD_IDENTIFIER_TYPE_TENDER_ID)
        self.assertTrue(classification["primary_load_identifier_candidate"])

    def test_po_and_bol_labels_are_negative_primary(self):
        self.assertTrue(is_negative_primary_identifier_label("PO #"))
        self.assertTrue(is_negative_primary_identifier_label("BOL #"))
        self.assertFalse(is_primary_load_identifier_label("PO #"))
        self.assertFalse(is_primary_load_identifier_label("BOL #"))

    def test_header_ref_is_medium_primary_reference(self):
        classification = classify_identifier_label(
            "Ref #",
            {"page_role": "header", "section_role": "load confirmation"},
        )

        self.assertEqual(classification["identifier_type"], LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE)
        self.assertTrue(classification["primary_load_identifier_candidate"])
        self.assertEqual(classification["confidence"], CANDIDATE_CONFIDENCE_MEDIUM)

    def test_stop_section_ref_is_not_primary(self):
        classification = classify_identifier_label(
            "Ref #",
            {"section_role": "pickup stop"},
        )

        self.assertFalse(classification["primary_load_identifier_candidate"])
        self.assertIn("ambiguous_reference_label", classification["warning_codes"])

    def test_customer_ref_is_not_primary_by_default(self):
        self.assertFalse(is_primary_load_identifier_label("Customer Ref"))
        self.assertTrue(is_negative_primary_identifier_label("Customer Ref"))

    def test_label_scoring_prefers_strong_primary(self):
        self.assertGreater(
            score_identifier_label("Load #"),
            score_identifier_label("Ref #", {"section_role": "pickup stop"}),
        )


if __name__ == "__main__":
    unittest.main()
