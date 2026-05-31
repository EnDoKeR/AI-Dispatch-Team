import unittest

from app.document_ai.stop_association import (
    STOP_FIELD_LOCATION,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_PICKUP,
    build_stop_association_result,
    build_stop_field_candidate,
    build_stop_group_candidate,
)
from app.document_ai.stop_group_provenance import (
    STOP_GROUP_SOURCE_TYPE_LINE_CLUSTER,
    build_stop_group_provenance,
)
from app.document_ai.stop_normalization import build_normalized_stop_set


def _cluster_group(group_id, stop_type=STOP_TYPE_PICKUP, sequence=1, grouping_key="p1|pu|1"):
    section_role = ""
    return build_stop_group_candidate(
        stop_group_id=group_id,
        stop_sequence=sequence,
        stop_type=stop_type,
        source="section_block",
        page_number=1,
        section_role=section_role,
        field_candidates=[
            build_stop_field_candidate(
                stop_group_id=group_id,
                stop_sequence=sequence,
                stop_type=stop_type,
                field_name=STOP_FIELD_LOCATION,
                candidate_id=f"{group_id}_location",
                confidence=0.85,
                evidence_ref={"line_id": group_id},
                source="section_block",
            )
        ],
        confidence=0.85,
        provenance=build_stop_group_provenance(
            source_type=STOP_GROUP_SOURCE_TYPE_LINE_CLUSTER,
            source_generator="synthetic_fixture",
            page_number=1,
            line_id=group_id,
            section_role=section_role,
            trigger_label_category=stop_type,
            candidate_field_names=[STOP_FIELD_LOCATION],
            grouping_key=grouping_key,
        ),
    )


class StopClusterDedupeTests(unittest.TestCase):
    def test_duplicate_clustered_section_removed(self):
        stop_set = build_normalized_stop_set(
            build_stop_association_result(
                stop_groups=[
                    _cluster_group("pu_a"),
                    _cluster_group("pu_b"),
                ]
            ),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(stop_set["stop_duplicate_removed_count"], 1)
        self.assertEqual(len(stop_set["stops"]), 1)

    def test_distinct_stop_sections_preserved(self):
        stop_set = build_normalized_stop_set(
            build_stop_association_result(
                stop_groups=[
                    _cluster_group("pu_a", sequence=1, grouping_key="p1|pu|1"),
                    _cluster_group("pu_b", sequence=2, grouping_key="p1|pu|2"),
                ]
            ),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(stop_set["stop_duplicate_removed_count"], 0)
        self.assertEqual(len(stop_set["stops"]), 2)

    def test_pickup_and_delivery_not_merged(self):
        stop_set = build_normalized_stop_set(
            build_stop_association_result(
                stop_groups=[
                    _cluster_group("pu_a", STOP_TYPE_PICKUP, 1, "p1|pu|1"),
                    _cluster_group("del_a", STOP_TYPE_DELIVERY, 2, "p1|del|2"),
                ]
            ),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(stop_set["stop_duplicate_removed_count"], 0)
        self.assertEqual(stop_set["pickup_count"], 1)
        self.assertEqual(stop_set["delivery_count"], 1)


if __name__ == "__main__":
    unittest.main()
