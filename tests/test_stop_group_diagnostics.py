import json
import unittest

from app.document_ai.stop_association import (
    STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
    STOP_ASSOCIATION_SOURCE_TABLE_ROW,
    STOP_FIELD_DATE,
    STOP_FIELD_LOCATION,
    STOP_FIELD_REFERENCE,
    STOP_FIELD_TIME,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_PICKUP,
    STOP_TYPE_UNKNOWN,
    build_stop_field_candidate,
    build_stop_group_candidate,
)
from app.document_ai.stop_group_diagnostics import (
    STOP_GROUP_QUALITY_AMBIGUOUS_REVIEW,
    STOP_GROUP_QUALITY_EMPTY,
    STOP_GROUP_QUALITY_NOISY,
    STOP_GROUP_QUALITY_NORMALIZED_READY,
    STOP_GROUP_QUALITY_USEFUL_BUT_UNMERGED,
    build_stop_group_diagnostics,
)


def _field(field_name):
    return build_stop_field_candidate(
        stop_group_id="group",
        field_name=field_name,
        candidate_id=f"{field_name}_candidate",
    )


class StopGroupDiagnosticsTests(unittest.TestCase):
    def test_zero_groups_is_empty(self):
        diagnostics = build_stop_group_diagnostics([])

        self.assertEqual(diagnostics["raw_group_count"], 0)
        self.assertEqual(diagnostics["quality_bucket"], STOP_GROUP_QUALITY_EMPTY)

    def test_duplicate_groups_are_noisy(self):
        group = build_stop_group_candidate(
            stop_group_id="group_001",
            stop_sequence=1,
            stop_type=STOP_TYPE_PICKUP,
            source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
            section_role="PICKUP_SECTION",
            field_candidates=[_field(STOP_FIELD_LOCATION)],
        )
        diagnostics = build_stop_group_diagnostics([group, dict(group), dict(group)])

        self.assertEqual(diagnostics["duplicate_like_group_count"], 2)
        self.assertEqual(diagnostics["quality_bucket"], STOP_GROUP_QUALITY_NOISY)

    def test_table_groups_with_stop_fields_are_normalized_ready(self):
        pickup = build_stop_group_candidate(
            "group_pickup",
            1,
            STOP_TYPE_PICKUP,
            STOP_ASSOCIATION_SOURCE_TABLE_ROW,
            table_id="T1",
            row_index=1,
            field_candidates=[
                _field(STOP_FIELD_LOCATION),
                _field(STOP_FIELD_DATE),
                _field(STOP_FIELD_TIME),
            ],
        )
        delivery = build_stop_group_candidate(
            "group_delivery",
            2,
            STOP_TYPE_DELIVERY,
            STOP_ASSOCIATION_SOURCE_TABLE_ROW,
            table_id="T1",
            row_index=2,
            field_candidates=[_field(STOP_FIELD_LOCATION), _field(STOP_FIELD_REFERENCE)],
        )
        diagnostics = build_stop_group_diagnostics([pickup, delivery])

        self.assertEqual(diagnostics["table_group_count"], 2)
        self.assertEqual(diagnostics["groups_with_reference"], 1)
        self.assertEqual(diagnostics["quality_bucket"], STOP_GROUP_QUALITY_NORMALIZED_READY)

    def test_signature_and_terms_noise_detected(self):
        signature = build_stop_group_candidate(
            "sig_group",
            stop_type=STOP_TYPE_UNKNOWN,
            source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
            section_role="SIGNATURE_BLOCK",
            warning_codes=["signature"],
        )
        terms = build_stop_group_candidate(
            "terms_group",
            stop_type=STOP_TYPE_UNKNOWN,
            source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
            section_role="LEGAL_TERMS",
        )

        diagnostics = build_stop_group_diagnostics([signature, terms])

        self.assertEqual(diagnostics["likely_signature_noise_count"], 1)
        self.assertEqual(diagnostics["likely_terms_noise_count"], 1)

    def test_ambiguous_groups_route_review(self):
        groups = [
            build_stop_group_candidate(
                f"group_{index}",
                stop_type=STOP_TYPE_UNKNOWN,
                source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
                page_number=index + 1,
                section_role="MULTI_STOP_SECTION",
                field_candidates=[_field(STOP_FIELD_LOCATION)],
            )
            for index in range(3)
        ]
        diagnostics = build_stop_group_diagnostics(groups)

        self.assertEqual(diagnostics["quality_bucket"], STOP_GROUP_QUALITY_AMBIGUOUS_REVIEW)

    def test_useful_but_unmerged_serializes_safely(self):
        group = build_stop_group_candidate(
            "group_pickup",
            1,
            STOP_TYPE_PICKUP,
            STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
            section_role="PICKUP_SECTION",
            field_candidates=[_field(STOP_FIELD_LOCATION)],
        )
        diagnostics = build_stop_group_diagnostics([group])
        payload = json.loads(json.dumps(diagnostics, sort_keys=True))

        self.assertEqual(payload["quality_bucket"], STOP_GROUP_QUALITY_USEFUL_BUT_UNMERGED)
        self.assertFalse(payload["raw_text_included"])
        self.assertTrue(payload["private_values_redacted"])
        self.assertNotIn("raw_text", payload)


if __name__ == "__main__":
    unittest.main()
