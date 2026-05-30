import json
import unittest

from app.document_ai.layout_artifacts import (
    EVIDENCE_TABLE_CELL,
    build_bounding_box,
    build_layout_evidence_ref,
)
from app.document_ai.layout_candidate_adapter import (
    attach_layout_evidence_to_candidate,
    build_field_candidate_from_layout_value,
    convert_label_value_candidates_to_field_candidates,
)
from app.document_ai.layout_proximity import PROXIMITY_TABLE_ROW, build_label_value_candidate
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    FIELD_PICKUP_LOCATION,
    FIELD_RATE,
    build_field_candidate,
)


def _fake_label_value(field="rate", value="$2800.00"):
    bbox = build_bounding_box(100, 100, 180, 120, page_number=1)
    evidence_ref = build_layout_evidence_ref(
        page_number=1,
        bbox=bbox,
        table_id="T_RATE",
        cell_ref="r1c1",
        label="Total Carrier Pay",
        evidence_type=EVIDENCE_TABLE_CELL,
    )
    return build_label_value_candidate(
        label="Total Carrier Pay",
        value_text_redacted=value,
        label_bbox=build_bounding_box(20, 100, 90, 120, page_number=1),
        value_bbox=bbox,
        page_number=1,
        proximity_type=PROXIMITY_TABLE_ROW,
        distance_score=0.91,
        confidence=CANDIDATE_CONFIDENCE_HIGH,
        reasons=["table_row_layout_pair"],
        evidence_ref=evidence_ref,
        source_field=field,
    )


class LayoutCandidateAdapterTests(unittest.TestCase):
    def test_create_rate_candidate_with_layout_evidence(self):
        candidate = build_field_candidate_from_layout_value(
            field_name=FIELD_RATE,
            label_value_candidate=_fake_label_value(),
            normalized_value="2800.00",
            value_type="total_carrier_pay",
            section_role="RATE_SUMMARY",
            page_role="PAYMENT_SUMMARY",
        )

        self.assertEqual(candidate["field_name"], FIELD_RATE)
        self.assertEqual(candidate["raw_value"], "$2800.00")
        self.assertEqual(candidate["normalized_value"], "2800.00")
        self.assertEqual(candidate["layout_table_id"], "T_RATE")
        self.assertEqual(candidate["layout_cell_ref"], "r1c1")
        self.assertEqual(candidate["layout_section_role"], "RATE_SUMMARY")
        self.assertEqual(candidate["layout_page_role"], "PAYMENT_SUMMARY")
        self.assertEqual(candidate["layout_proximity_type"], PROXIMITY_TABLE_ROW)

    def test_create_stop_candidate_with_section_role(self):
        label_value = _fake_label_value(field="pickup_location", value="FAKE ORIGIN ST")
        candidate = build_field_candidate_from_layout_value(
            field_name=FIELD_PICKUP_LOCATION,
            label_value_candidate=label_value,
            section_role="PICKUP_SECTION",
            page_role="STOP_DETAILS",
        )

        self.assertEqual(candidate["field_name"], FIELD_PICKUP_LOCATION)
        self.assertEqual(candidate["layout_section_role"], "PICKUP_SECTION")
        self.assertEqual(candidate["layout_page_role"], "STOP_DETAILS")

    def test_candidate_serializes_with_layout_evidence(self):
        candidate = build_field_candidate_from_layout_value(
            field_name=FIELD_RATE,
            label_value_candidate=_fake_label_value(),
        )

        payload = json.loads(json.dumps(candidate))

        self.assertEqual(payload["layout_evidence_ref"]["table_id"], "T_RATE")
        self.assertIn("layout_proximity", payload["confidence_reasons"][-1])

    def test_attach_layout_evidence_to_existing_candidate_is_backward_compatible(self):
        old_candidate = build_field_candidate(field_name=FIELD_RATE, raw_value="$100.00")
        evidence = _fake_label_value()["evidence_ref"]

        enriched = attach_layout_evidence_to_candidate(
            old_candidate,
            layout_evidence_ref=evidence,
            section_role="RATE_SUMMARY",
        )

        self.assertEqual(old_candidate["raw_value"], enriched["raw_value"])
        self.assertEqual(enriched["layout_section_role"], "RATE_SUMMARY")
        self.assertEqual(enriched["layout_evidence_ref"]["table_id"], "T_RATE")

    def test_convert_label_value_candidates(self):
        candidates = convert_label_value_candidates_to_field_candidates(
            FIELD_RATE,
            [_fake_label_value(), _fake_label_value(value="$3000.00")],
            value_type="rate_amount",
            section_role="RATE_SUMMARY",
        )

        self.assertEqual(len(candidates), 2)
        self.assertTrue(all(candidate["field_name"] == FIELD_RATE for candidate in candidates))
        self.assertTrue(all(candidate["layout_section_role"] == "RATE_SUMMARY" for candidate in candidates))


if __name__ == "__main__":
    unittest.main()
