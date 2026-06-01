import unittest

from app.document_ai.ratecon_canonical_fields import (
    FIELD_ACCESSORIAL_TERM,
    FIELD_DELIVERY_LOCATION,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_LOCATION,
    FIELD_REFERENCE_NUMBERS,
    FIELD_TOTAL_CARRIER_RATE,
    MAPPING_MEDIUM,
    MAPPING_STRONG,
    MAPPING_WEAK,
    canonical_field_mapping,
    confidence_after_mapping,
)


class RateConCanonicalFieldTests(unittest.TestCase):
    def test_load_identity_aliases_map_with_strength(self):
        self.assertEqual(
            canonical_field_mapping("load_id").canonical_field,
            FIELD_LOAD_NUMBER,
        )
        self.assertEqual(canonical_field_mapping("load_id").strength, MAPPING_STRONG)
        self.assertEqual(
            canonical_field_mapping("shipment_number").canonical_field,
            FIELD_LOAD_NUMBER,
        )
        self.assertEqual(
            canonical_field_mapping("shipment_number").strength,
            MAPPING_MEDIUM,
        )
        self.assertEqual(
            canonical_field_mapping("order_number").canonical_field,
            FIELD_LOAD_NUMBER,
        )
        self.assertEqual(
            canonical_field_mapping("order_number").strength,
            MAPPING_MEDIUM,
        )

    def test_po_and_bol_are_not_strong_load_numbers(self):
        self.assertEqual(
            canonical_field_mapping("po_number").canonical_field,
            FIELD_REFERENCE_NUMBERS,
        )
        self.assertEqual(
            canonical_field_mapping("bol_number").canonical_field,
            FIELD_REFERENCE_NUMBERS,
        )
        self.assertNotEqual(
            canonical_field_mapping("po_number").canonical_field,
            FIELD_LOAD_NUMBER,
        )

    def test_rate_aliases_and_negative_money_contexts(self):
        self.assertEqual(
            canonical_field_mapping("carrier_pay").canonical_field,
            FIELD_TOTAL_CARRIER_RATE,
        )
        self.assertEqual(
            canonical_field_mapping("carrier_pay").strength,
            MAPPING_STRONG,
        )
        self.assertEqual(
            canonical_field_mapping("fuel_surcharge").canonical_field,
            FIELD_ACCESSORIAL_TERM,
        )
        self.assertNotEqual(
            canonical_field_mapping("fuel_surcharge").canonical_field,
            FIELD_TOTAL_CARRIER_RATE,
        )

    def test_stop_and_party_aliases(self):
        self.assertEqual(
            canonical_field_mapping("pickup_location").canonical_field,
            FIELD_PICKUP_LOCATION,
        )
        self.assertEqual(
            canonical_field_mapping("consignee").canonical_field,
            FIELD_DELIVERY_LOCATION,
        )
        self.assertEqual(
            canonical_field_mapping("consignee").strength,
            MAPPING_MEDIUM,
        )

    def test_weak_mapping_caps_confidence(self):
        self.assertEqual(confidence_after_mapping(0.9, MAPPING_WEAK), 0.62)


if __name__ == "__main__":
    unittest.main()
