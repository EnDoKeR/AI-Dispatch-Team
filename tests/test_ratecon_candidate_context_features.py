import unittest

from app.document_ai.ratecon_candidate_context_features import enrich_candidate_context


class RateconCandidateContextFeatureTests(unittest.TestCase):
    def test_header_po_can_be_primary_load_identity_context(self):
        candidate = enrich_candidate_context(
            {
                "field": "reference_numbers",
                "label": "PO #",
                "evidence_text": "Rate Confirmation for PO # value present",
                "metadata": {"section_context": "load_info"},
            }
        )
        metadata = candidate["metadata"]

        self.assertEqual(metadata["id_type_hint"], "po")
        self.assertTrue(metadata["is_document_title_or_header_id"])
        self.assertTrue(metadata["context_feature_load_identity_candidate"])
        self.assertGreaterEqual(metadata["id_role_confidence"], 0.65)

    def test_stop_pickup_reference_is_penalized_for_primary_load(self):
        candidate = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Pickup #",
                "evidence_text": "Pickup # value present",
                "metadata": {"section_context": "pickup"},
            }
        )
        metadata = candidate["metadata"]

        self.assertTrue(metadata["is_stop_level_reference"])
        self.assertTrue(metadata["is_pickup_delivery_reference"])
        self.assertEqual(metadata["context_penalty_reason"], "pickup_delivery_reference")

    def test_bol_reference_in_stop_section_is_weak(self):
        candidate = enrich_candidate_context(
            {
                "field": "reference_numbers",
                "label": "BOL #",
                "evidence_text": "Delivery BOL # value present",
                "metadata": {"section_context": "delivery"},
            }
        )
        metadata = candidate["metadata"]

        self.assertEqual(metadata["id_type_hint"], "bol")
        self.assertTrue(metadata["is_bol_or_po_or_customer_ref"])
        self.assertTrue(metadata["is_stop_level_reference"])
        self.assertFalse(metadata["context_feature_load_identity_candidate"])

    def test_driver_truck_trailer_ids_are_noise(self):
        candidate = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Truck ID",
                "evidence_text": "Truck ID value present",
                "metadata": {},
            }
        )
        metadata = candidate["metadata"]

        self.assertTrue(metadata["is_driver_truck_trailer_noise"])
        self.assertEqual(metadata["context_penalty_reason"], "driver_truck_trailer_noise")

    def test_money_total_and_negative_contexts(self):
        total = enrich_candidate_context(
            {
                "field": "total_carrier_rate",
                "label": "Total Carrier Pay",
                "evidence_text": "Total Carrier Pay amount present",
                "metadata": {},
            }
        )
        accessorial = enrich_candidate_context(
            {
                "field": "total_carrier_rate",
                "label": "QuickPay Fee",
                "evidence_text": "QuickPay fee amount present",
                "metadata": {},
            }
        )

        self.assertEqual(total["metadata"]["money_context"], "total_carrier_pay")
        self.assertTrue(total["metadata"]["is_total_pay_candidate"])
        self.assertEqual(accessorial["metadata"]["money_context"], "quickpay")
        self.assertTrue(accessorial["metadata"]["is_deduction_or_penalty"])


if __name__ == "__main__":
    unittest.main()
