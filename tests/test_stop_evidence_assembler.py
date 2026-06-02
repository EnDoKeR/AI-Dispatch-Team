import unittest

from app.document_ai.field_candidate_provenance import build_field_candidate
from app.document_ai.stop_evidence_assembler import (
    EVIDENCE_DATE,
    EVIDENCE_FACILITY,
    ROLE_DELIVERY,
    ROLE_PICKUP,
    associate_stop_evidence_by_proximity,
    assemble_stop_candidates,
    extract_stop_evidence_from_candidates,
)


def candidate(field, value, label="", confidence=0.75):
    return build_field_candidate(
        field=field,
        value=value,
        normalized_value=value,
        label=label or field,
        evidence_text=f"{label or field}: {value}",
        page=1,
        source="native_text",
        parser_name="fake_generator",
        confidence=confidence,
    )


class StopEvidenceAssemblerTests(unittest.TestCase):
    def test_pickup_date_candidate_becomes_pickup_date_evidence(self):
        evidence = extract_stop_evidence_from_candidates(
            [candidate("pickup_date", "06/10/2026")]
        )

        self.assertEqual(evidence[0]["role"], ROLE_PICKUP)
        self.assertEqual(evidence[0]["evidence_type"], EVIDENCE_DATE)

    def test_delivery_location_candidate_becomes_delivery_location_evidence(self):
        evidence = extract_stop_evidence_from_candidates(
            [candidate("delivery_location", "Fake Destination, FS")]
        )

        self.assertEqual(evidence[0]["role"], ROLE_DELIVERY)
        self.assertIn(
            evidence[0]["evidence_type"],
            {"city_state_zip", EVIDENCE_FACILITY},
        )

    def test_shipper_origin_and_consignee_destination_roles(self):
        evidence = extract_stop_evidence_from_candidates(
            [
                candidate("shipper", "Fake Origin Facility"),
                candidate("destination", "Fake Destination Facility"),
            ]
        )

        roles = [item["role"] for item in evidence]
        self.assertIn(ROLE_PICKUP, roles)
        self.assertIn(ROLE_DELIVERY, roles)

    def test_location_and_date_assemble_structured_pickup_stop(self):
        evidence = extract_stop_evidence_from_candidates(
            [
                candidate("pickup_location", "Fake Origin Facility"),
                candidate("pickup_date", "06/10/2026"),
            ]
        )

        assembled = assemble_stop_candidates(evidence)

        self.assertEqual(len(assembled), 1)
        self.assertEqual(assembled[0]["field"], "pickup_stops")
        self.assertTrue(assembled[0]["metadata"]["assembled_from_partial_evidence"])
        self.assertTrue(assembled[0]["metadata"]["has_location"])
        self.assertTrue(assembled[0]["metadata"]["has_date"])
        self.assertEqual(assembled[0]["metadata"]["evidence_count"], 2)
        self.assertGreaterEqual(assembled[0]["confidence"], 0.65)

    def test_delivery_location_and_date_assemble_structured_delivery_stop(self):
        evidence = extract_stop_evidence_from_candidates(
            [
                candidate("delivery_location", "Fake Destination Facility"),
                candidate("delivery_date", "06/11/2026"),
            ]
        )

        assembled = assemble_stop_candidates(evidence)

        self.assertEqual(assembled[0]["field"], "delivery_stops")
        self.assertTrue(assembled[0]["metadata"]["has_location"])
        self.assertTrue(assembled[0]["metadata"]["has_date"])

    def test_date_only_produces_partial_low_confidence_stop_candidate(self):
        evidence = extract_stop_evidence_from_candidates(
            [candidate("pickup_date", "06/10/2026")]
        )

        assembled = assemble_stop_candidates(evidence)

        self.assertEqual(assembled[0]["field"], "pickup_stops")
        self.assertTrue(assembled[0]["metadata"]["partial_only"])
        self.assertLessEqual(assembled[0]["confidence"], 0.55)

    def test_multiple_locations_and_dates_are_marked_ambiguous(self):
        evidence = extract_stop_evidence_from_candidates(
            [
                candidate("pickup_location", "Fake Origin A"),
                candidate("pickup_location", "Fake Origin B"),
                candidate("pickup_date", "06/10/2026"),
                candidate("pickup_date", "06/11/2026"),
            ]
        )

        assembled = assemble_stop_candidates(evidence)

        self.assertTrue(assembled[0]["metadata"]["ambiguous_stop_candidate"])
        self.assertLessEqual(assembled[0]["confidence"], 0.60)

    def test_proximity_clusters_near_pickup_location_and_date(self):
        artifact = {
            "pages": [
                {
                    "page_number": 1,
                    "text": "Pickup\nFake Origin Facility\n06/10/2026\nDelivery\nFake Destination",
                }
            ]
        }
        evidence = extract_stop_evidence_from_candidates(
            [
                candidate("pickup_location", "Fake Origin Facility"),
                candidate("pickup_date", "06/10/2026"),
            ],
            artifact=artifact,
        )

        stop_candidates, summary = associate_stop_evidence_by_proximity(evidence)

        self.assertEqual(summary["clusters_with_location_and_date"], 1)
        self.assertEqual(stop_candidates[0]["metadata"]["proximity_cluster_line_span"], [1, 2])
        self.assertGreaterEqual(stop_candidates[0]["confidence"], 0.65)

    def test_far_location_and_date_remain_partial_clusters(self):
        evidence = [
            {
                "role": "pickup",
                "evidence_type": "facility",
                "value": "Fake Origin",
                "normalized_value": "Fake Origin",
                "page": 1,
                "line_index": 1,
            },
            {
                "role": "pickup",
                "evidence_type": "date",
                "value": "06/10/2026",
                "normalized_value": "06/10/2026",
                "page": 1,
                "line_index": 20,
            },
        ]

        stop_candidates, summary = associate_stop_evidence_by_proximity(evidence)

        self.assertEqual(summary["proximity_cluster_count"], 2)
        self.assertEqual(summary["clusters_with_location_and_date"], 0)
        self.assertIn(
            "STOP_PROXIMITY_NO_LOCATION_DATE_PAIR",
            summary["ambiguity_reason_counts"],
        )

    def test_delivery_evidence_does_not_complete_pickup_cluster(self):
        evidence = [
            {
                "role": "pickup",
                "evidence_type": "facility",
                "value": "Fake Origin",
                "page": 1,
                "line_index": 1,
            },
            {
                "role": "delivery",
                "evidence_type": "date",
                "value": "06/10/2026",
                "page": 1,
                "line_index": 2,
            },
        ]

        stop_candidates, summary = associate_stop_evidence_by_proximity(evidence)

        self.assertEqual(summary["clusters_with_location_and_date"], 0)
        self.assertEqual({item["role"] for item in stop_candidates}, {"pickup", "delivery"})

    def test_missing_line_index_reports_proximity_reason(self):
        evidence = [
            {
                "role": "pickup",
                "evidence_type": "facility",
                "value": "Fake Origin",
                "page": 1,
                "line_index": "",
            }
        ]

        _stop_candidates, summary = associate_stop_evidence_by_proximity(evidence)

        self.assertIn(
            "STOP_PROXIMITY_MISSING_LINE_INDEX",
            summary["ambiguity_reason_counts"],
        )


if __name__ == "__main__":
    unittest.main()
