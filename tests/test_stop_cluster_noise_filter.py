import unittest

from app.document_ai.stop_association import (
    STOP_FIELD_DATE,
    STOP_FIELD_LOCATION,
    STOP_TYPE_PICKUP,
    build_stop_association_result,
    build_stop_field_candidate,
    build_stop_group_candidate,
)
from app.document_ai.stop_group_provenance import (
    STOP_GROUP_SOURCE_TYPE_SINGLE_LINE,
    build_stop_group_provenance,
)
from app.document_ai.stop_normalization import build_normalized_stop_set


def _single_line_group(group_id, section_role, fields=None, warnings=None):
    field_candidates = []
    for field_name in fields or []:
        field_candidates.append(
            build_stop_field_candidate(
                stop_group_id=group_id,
                stop_type=STOP_TYPE_PICKUP,
                field_name=field_name,
                candidate_id=f"{group_id}_{field_name}",
                confidence=0.8,
                evidence_ref={"line_id": group_id},
                source="section_block",
            )
        )
    return build_stop_group_candidate(
        stop_group_id=group_id,
        stop_sequence=1,
        stop_type=STOP_TYPE_PICKUP,
        source="section_block",
        page_number=1,
        section_role=section_role,
        field_candidates=field_candidates,
        confidence=0.8,
        warning_codes=warnings or [],
        provenance=build_stop_group_provenance(
            source_type=STOP_GROUP_SOURCE_TYPE_SINGLE_LINE,
            source_generator="synthetic_fixture",
            page_number=1,
            line_id=group_id,
            section_role=section_role,
            trigger_label_category="pickup",
            candidate_field_names=fields or [],
            grouping_key=f"p1|{section_role}|{group_id}",
            warning_codes=warnings or [],
        ),
    )


class StopClusterNoiseFilterTests(unittest.TestCase):
    def test_signature_only_cluster_removed(self):
        stop_set = build_normalized_stop_set(
            build_stop_association_result(
                stop_groups=[_single_line_group("sig", "SIGNATURE_BLOCK", warnings=["signature"])]
            ),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(stop_set["stop_noise_removed_count"], 1)
        self.assertEqual(len(stop_set["stops"]), 0)

    def test_terms_billing_cluster_removed_without_strong_stop_evidence(self):
        stop_set = build_normalized_stop_set(
            build_stop_association_result(
                stop_groups=[
                    _single_line_group("terms", "BILLING_INSTRUCTIONS", fields=[STOP_FIELD_DATE])
                ]
            ),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(stop_set["stop_noise_removed_count"], 1)
        self.assertEqual(len(stop_set["stops"]), 0)

    def test_real_stop_cluster_preserved(self):
        stop_set = build_normalized_stop_set(
            build_stop_association_result(
                stop_groups=[
                    _single_line_group("pu_loc", "PICKUP_SECTION", fields=[STOP_FIELD_LOCATION]),
                    _single_line_group("pu_date", "PICKUP_SECTION", fields=[STOP_FIELD_DATE]),
                ]
            ),
            classification_result={"document_alias": "RATECON_FAKE", "normal_load_movement": True},
        )

        self.assertEqual(stop_set["stop_noise_removed_count"], 0)
        self.assertEqual(len(stop_set["stops"]), 1)


if __name__ == "__main__":
    unittest.main()
