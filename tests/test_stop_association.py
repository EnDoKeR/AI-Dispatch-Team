import json
import unittest

from app.document_ai.stop_association import (
    STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
    STOP_ASSOCIATION_SOURCE_TABLE_ROW,
    STOP_ASSOCIATION_VERSION,
    STOP_FIELD_DATE,
    STOP_FIELD_LOCATION,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_PICKUP,
    STOP_TYPE_UNKNOWN,
    build_stop_association_result,
    build_stop_field_candidate,
    build_stop_group_candidate,
)
from app.document_ai.stop_group_provenance import (
    STOP_GROUP_SOURCE_TYPE_TABLE_ROW,
    build_stop_group_provenance,
)


class StopAssociationContractTests(unittest.TestCase):
    def test_create_pickup_group_from_table_row(self):
        location = build_stop_field_candidate(
            stop_group_id="stop_001",
            stop_sequence=1,
            stop_type=STOP_TYPE_PICKUP,
            field_name=STOP_FIELD_LOCATION,
            candidate_id="pickup_location_1",
            confidence=0.9,
            evidence_ref={"table_id": "table_1", "cell_ref": "r1c2"},
            source=STOP_ASSOCIATION_SOURCE_TABLE_ROW,
        )
        group = build_stop_group_candidate(
            stop_group_id="stop_001",
            stop_sequence=1,
            stop_type=STOP_TYPE_PICKUP,
            source=STOP_ASSOCIATION_SOURCE_TABLE_ROW,
            table_id="table_1",
            row_index=1,
            field_candidates=[location],
            confidence=0.9,
        )

        self.assertEqual(group["stop_type"], STOP_TYPE_PICKUP)
        self.assertEqual(group["source"], STOP_ASSOCIATION_SOURCE_TABLE_ROW)
        self.assertEqual(group["field_candidates"][0]["field_name"], STOP_FIELD_LOCATION)
        self.assertEqual(group["provenance"], {})

    def test_group_candidate_accepts_safe_provenance(self):
        provenance = build_stop_group_provenance(
            source_type=STOP_GROUP_SOURCE_TYPE_TABLE_ROW,
            source_generator="test_builder",
            page_number=1,
            table_id="table_1",
            row_index=1,
            candidate_field_names=[STOP_FIELD_LOCATION],
            grouping_key="1|table_1|1",
        )

        group = build_stop_group_candidate(
            stop_group_id="stop_001",
            stop_sequence=1,
            stop_type=STOP_TYPE_PICKUP,
            source=STOP_ASSOCIATION_SOURCE_TABLE_ROW,
            table_id="table_1",
            row_index=1,
            field_candidates=[],
            provenance=provenance,
        )

        self.assertEqual(group["provenance"]["source_type"], STOP_GROUP_SOURCE_TYPE_TABLE_ROW)
        self.assertEqual(group["provenance"]["grouping_key"], "1|table_1|1")
        self.assertFalse(group["provenance"]["raw_text_included"])
        self.assertTrue(group["provenance"]["private_values_redacted"])

    def test_create_delivery_group_from_section_block(self):
        date = build_stop_field_candidate(
            stop_group_id="stop_002",
            stop_sequence=2,
            stop_type=STOP_TYPE_DELIVERY,
            field_name=STOP_FIELD_DATE,
            candidate_id="delivery_date_1",
            confidence=0.8,
            source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
        )
        group = build_stop_group_candidate(
            stop_group_id="stop_002",
            stop_sequence=2,
            stop_type=STOP_TYPE_DELIVERY,
            source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
            section_role="DELIVERY_SECTION",
            field_candidates=[date],
        )

        self.assertEqual(group["stop_type"], STOP_TYPE_DELIVERY)
        self.assertEqual(group["section_role"], "DELIVERY_SECTION")

    def test_multi_stop_groups_are_preserved(self):
        pickup = build_stop_group_candidate("stop_001", 1, STOP_TYPE_PICKUP)
        delivery = build_stop_group_candidate("stop_002", 2, STOP_TYPE_DELIVERY)

        result = build_stop_association_result(stop_groups=[pickup, delivery])

        self.assertEqual(len(result["stop_groups"]), 2)
        self.assertEqual(result["association_version"], STOP_ASSOCIATION_VERSION)

    def test_ambiguous_stop_type_remains_unknown(self):
        group = build_stop_group_candidate(
            stop_group_id="stop_unknown",
            stop_type="not sure",
            warning_codes=["ambiguous_stop_type"],
        )

        self.assertEqual(group["stop_type"], STOP_TYPE_UNKNOWN)
        self.assertIn("ambiguous_stop_type", group["warning_codes"])

    def test_result_serializes(self):
        result = build_stop_association_result(
            stop_groups=[build_stop_group_candidate("stop_001", 1, STOP_TYPE_PICKUP)],
            unresolved_stop_fields=["delivery_date"],
            conflict_stop_fields=["pickup_location"],
            warning_codes=["review_required"],
        )

        text = json.dumps(result, sort_keys=True)

        self.assertIn("stop_association_v1", text)
        self.assertIn("delivery_date", text)


if __name__ == "__main__":
    unittest.main()
