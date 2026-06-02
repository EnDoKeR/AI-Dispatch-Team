import unittest

from app.document_ai.ratecon_candidate_context_features import enrich_candidate_context
from app.document_ai.ratecon_load_table_safety import (
    TABLE_NEIGHBOR_SELECTION_ABSTAIN,
    TABLE_NEIGHBOR_SELECTION_ALLOWED,
    apply_table_abstention_profile_to_candidates,
    TABLE_NEIGHBOR_RISKY,
    TABLE_NEIGHBOR_SAFE,
    TABLE_NEIGHBOR_UNSAFE,
    apply_table_safety_profile,
)


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

    def test_safe_header_table_load_candidate_is_marked_safe(self):
        candidate = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Load #",
                "evidence_text": "Load # table value present",
                "confidence": 0.86,
                "metadata": {
                    "table_cell_candidate": True,
                    "pairing_method": "table_key_value_row",
                    "table_context_role": "header_load_info",
                    "table_row_role": "load_id_row",
                    "id_type_hint": "load",
                    "label_strength": "strong",
                },
            }
        )

        self.assertEqual(candidate["metadata"]["table_neighbor_safety"], TABLE_NEIGHBOR_SAFE)
        self.assertEqual(candidate["confidence"], 0.86)

    def test_unsafe_stop_reference_table_candidate_is_demoted_by_profile(self):
        candidate = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Pickup #",
                "evidence_text": "Pickup # table value present",
                "confidence": 0.86,
                "metadata": {
                    "table_cell_candidate": True,
                    "pairing_method": "table_key_value_row",
                    "table_context_role": "stop_table",
                    "table_row_role": "pickup_delivery_ref_row",
                    "id_type_hint": "pickup_ref",
                },
            }
        )
        adjusted = apply_table_safety_profile(candidate)

        self.assertEqual(adjusted["metadata"]["table_neighbor_safety"], TABLE_NEIGHBOR_UNSAFE)
        self.assertEqual(adjusted["field"], "reference_numbers")
        self.assertLessEqual(adjusted["confidence"], 0.35)
        self.assertTrue(adjusted["metadata"]["table_neighbor_demoted_from_load_number"])

    def test_risky_multi_value_table_candidate_stays_diagnostic_low_confidence(self):
        candidate = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Order #",
                "evidence_text": "Order # table value present",
                "confidence": 0.74,
                "metadata": {
                    "table_cell_candidate": True,
                    "pairing_method": "table_key_value_row",
                    "table_context_role": "unknown",
                    "table_row_role": "unknown",
                    "table_row_identifier_like_cell_count": 3,
                    "id_type_hint": "order",
                    "label_strength": "medium",
                },
            }
        )
        adjusted = apply_table_safety_profile(candidate)

        self.assertEqual(adjusted["metadata"]["table_neighbor_safety"], TABLE_NEIGHBOR_RISKY)
        self.assertEqual(adjusted["field"], "load_number")
        self.assertLessEqual(adjusted["confidence"], 0.55)

    def test_rate_and_contact_table_candidates_are_unsafe(self):
        for role, penalty in [
            ("rate_table", "rate_or_money_table"),
            ("carrier_contact_table", "carrier_contact_table"),
            ("signature_footer", "signature_footer_table"),
        ]:
            with self.subTest(role=role):
                candidate = enrich_candidate_context(
                    {
                        "field": "load_number",
                        "label": "Load #",
                        "evidence_text": "Load # table value present",
                        "confidence": 0.86,
                        "metadata": {
                            "table_cell_candidate": True,
                            "pairing_method": "table_key_value_row",
                            "table_context_role": role,
                            "id_type_hint": "load",
                        },
                    }
                )
                self.assertEqual(candidate["metadata"]["table_neighbor_safety"], TABLE_NEIGHBOR_UNSAFE)
                self.assertEqual(candidate["metadata"]["table_neighbor_penalty_reason"], penalty)

    def test_table_abstention_allows_clear_load_info_key_value_row(self):
        candidate = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Load #",
                "evidence_text": "Load # table value present",
                "confidence": 0.84,
                "metadata": {
                    "table_cell_candidate": True,
                    "pairing_method": "table_key_value_row",
                    "table_context_role": "header_load_info",
                    "table_row_role": "load_id_row",
                    "id_type_hint": "load",
                    "label_strength": "strong",
                    "id_like_cell_count_in_row": 1,
                    "load_label_cell_count_in_row": 1,
                },
            }
        )

        adjusted = apply_table_abstention_profile_to_candidates([candidate])[0]

        self.assertEqual(adjusted["field"], "load_number")
        self.assertEqual(adjusted["metadata"]["selection_policy"], TABLE_NEIGHBOR_SELECTION_ALLOWED)
        self.assertFalse(adjusted["metadata"]["table_neighbor_abstained"])

    def test_table_abstention_demotes_mixed_reference_row(self):
        candidate = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Order #",
                "evidence_text": "Order # Ref # table value present",
                "confidence": 0.84,
                "metadata": {
                    "table_cell_candidate": True,
                    "pairing_method": "table_key_value_row",
                    "table_context_role": "header_load_info",
                    "table_row_role": "load_id_row",
                    "id_type_hint": "order",
                    "label_strength": "medium",
                    "id_like_cell_count_in_row": 2,
                    "load_label_cell_count_in_row": 1,
                    "reference_label_cell_count_in_row": 1,
                },
            }
        )

        adjusted = apply_table_abstention_profile_to_candidates([candidate])[0]

        self.assertEqual(adjusted["field"], "reference_numbers")
        self.assertEqual(adjusted["metadata"]["selection_policy"], TABLE_NEIGHBOR_SELECTION_ABSTAIN)
        self.assertTrue(adjusted["metadata"]["table_neighbor_abstained"])
        self.assertEqual(
            adjusted["metadata"]["table_neighbor_abstention_reason"],
            "table_neighbor_mixed_stop_reference_load_row",
        )

    def test_strong_header_candidate_causes_ambiguous_table_neighbor_to_abstain(self):
        header = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Load #",
                "evidence_text": "Load # header value present",
                "confidence": 0.86,
                "metadata": {
                    "document_region": "header",
                    "id_type_hint": "load",
                    "is_document_title_or_header_id": True,
                },
            }
        )
        table = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Order #",
                "evidence_text": "Order # table value present",
                "confidence": 0.82,
                "metadata": {
                    "table_cell_candidate": True,
                    "pairing_method": "table_key_value_row",
                    "table_context_role": "header_load_info",
                    "table_row_role": "load_id_row",
                    "id_type_hint": "order",
                    "label_strength": "medium",
                    "id_like_cell_count_in_row": 2,
                    "load_label_cell_count_in_row": 1,
                },
            }
        )

        adjusted = apply_table_abstention_profile_to_candidates([header, table])
        table_adjusted = adjusted[1]

        self.assertEqual(table_adjusted["field"], "reference_numbers")
        self.assertEqual(
            table_adjusted["metadata"]["table_neighbor_abstention_reason"],
            "table_neighbor_strong_header_candidate_elsewhere",
        )

    def test_table_abstention_keeps_weak_only_candidate_low_confidence(self):
        candidate = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Shipment #",
                "evidence_text": "Shipment # table value present",
                "confidence": 0.80,
                "metadata": {
                    "table_cell_candidate": True,
                    "pairing_method": "table_key_value_row",
                    "table_context_role": "header_load_info",
                    "table_row_role": "load_id_row",
                    "id_type_hint": "shipment",
                    "label_strength": "medium",
                    "id_like_cell_count_in_row": 1,
                },
            }
        )

        adjusted = apply_table_abstention_profile_to_candidates([candidate])[0]

        self.assertEqual(adjusted["field"], "load_number")
        self.assertEqual(adjusted["metadata"]["selection_policy"], "weak_only")
        self.assertLessEqual(adjusted["confidence"], 0.55)

    def test_header_row_table_key_value_candidate_abstains(self):
        candidate = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Load #",
                "evidence_text": "Load # table header neighbor present",
                "confidence": 0.88,
                "metadata": {
                    "table_cell_candidate": True,
                    "pairing_method": "table_key_value_row",
                    "table_context_role": "header_load_info",
                    "table_row_role": "header",
                    "id_type_hint": "load",
                    "label_strength": "strong",
                    "id_like_cell_count_in_row": 1,
                    "load_label_cell_count_in_row": 1,
                },
            }
        )

        adjusted = apply_table_abstention_profile_to_candidates([candidate])[0]

        self.assertEqual(adjusted["field"], "reference_numbers")
        self.assertEqual(
            adjusted["metadata"]["table_neighbor_abstention_reason"],
            "table_neighbor_header_row_key_value_unclear",
        )

    def test_header_value_column_candidate_remains_allowed(self):
        candidate = enrich_candidate_context(
            {
                "field": "load_number",
                "label": "Load #",
                "evidence_text": "Load # header value below present",
                "confidence": 0.80,
                "metadata": {
                    "table_cell_candidate": True,
                    "pairing_method": "table_header_value_column",
                    "table_context_role": "header_load_info",
                    "table_row_role": "unknown",
                    "id_type_hint": "load",
                    "label_strength": "strong",
                    "id_like_cell_count_in_row": 1,
                },
            }
        )

        adjusted = apply_table_abstention_profile_to_candidates([candidate])[0]

        self.assertEqual(adjusted["field"], "load_number")
        self.assertEqual(adjusted["metadata"]["selection_policy"], TABLE_NEIGHBOR_SELECTION_ALLOWED)


if __name__ == "__main__":
    unittest.main()
