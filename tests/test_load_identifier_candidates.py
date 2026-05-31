import json
import unittest

from app.document_ai.load_identifier_candidates import (
    LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
    LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
    LOAD_IDENTIFIER_TYPE_PO_NUMBER,
    build_load_identifier_candidate,
    is_primary_load_identifier_type,
    normalize_identifier_type,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    FIELD_LOAD_NUMBER,
    FIELD_REFERENCE,
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


if __name__ == "__main__":
    unittest.main()
