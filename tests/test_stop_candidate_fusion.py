import unittest

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_DELIVERY_DATE,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    SOURCE_REGEX,
    build_candidate_extraction_result,
    build_field_candidate,
)
from app.document_ai.stop_association import (
    STOP_ASSOCIATION_SOURCE_TABLE_ROW,
    STOP_FIELD_DATE,
    STOP_FIELD_LOCATION,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_PICKUP,
    build_stop_association_result,
    build_stop_field_candidate,
    build_stop_group_candidate,
    fuse_stop_candidates,
)


class StopCandidateFusionTests(unittest.TestCase):
    def _text_result(self, candidates):
        return build_candidate_extraction_result(candidates=candidates)

    def _text_candidate(self, field_name, value, confidence=CANDIDATE_CONFIDENCE_HIGH):
        return build_field_candidate(
            field_name=field_name,
            raw_value=value,
            normalized_value=value,
            confidence=confidence,
            source=SOURCE_REGEX,
            candidate_id=f"text_{field_name}",
        )

    def _layout_group(self, stop_type, field_name, value="", confidence=0.9):
        candidate = build_stop_field_candidate(
            stop_group_id=f"{stop_type}_group",
            stop_sequence=1,
            stop_type=stop_type,
            field_name=field_name,
            candidate_id=f"layout_{stop_type}_{field_name}",
            confidence=confidence,
            source=STOP_ASSOCIATION_SOURCE_TABLE_ROW,
        )
        if value:
            candidate["normalized_value"] = value
        group = build_stop_group_candidate(
            stop_group_id=f"{stop_type}_group",
            stop_sequence=1,
            stop_type=stop_type,
            source=STOP_ASSOCIATION_SOURCE_TABLE_ROW,
            field_candidates=[candidate],
            confidence=confidence,
        )
        return build_stop_association_result(stop_groups=[group])

    def test_strong_layout_improves_missing_stop_date(self):
        result = fuse_stop_candidates(
            self._text_result([]),
            self._layout_group(STOP_TYPE_PICKUP, STOP_FIELD_DATE, "2099-01-10"),
            baseline_resolution_result={
                "field_statuses": {FIELD_PICKUP_DATE: "missing"},
            },
        )

        self.assertIn(FIELD_PICKUP_DATE, result["improved_fields"])
        self.assertEqual(result["worsened_fields"], [])

    def test_weak_layout_does_not_overwrite_strong_text_pickup_location(self):
        result = fuse_stop_candidates(
            self._text_result(
                [self._text_candidate(FIELD_PICKUP_LOCATION, "FAKE ORIGIN")]
            ),
            self._layout_group(
                STOP_TYPE_PICKUP,
                STOP_FIELD_LOCATION,
                "FAKE OTHER ORIGIN",
                confidence=0.35,
            ),
            baseline_resolution_result={
                "field_statuses": {FIELD_PICKUP_LOCATION: "resolved"},
            },
        )

        self.assertNotIn(FIELD_PICKUP_LOCATION, result["worsened_fields"])
        self.assertIn(FIELD_PICKUP_LOCATION, result["unchanged_fields"])

    def test_conflicting_strong_delivery_date_routes_review(self):
        result = fuse_stop_candidates(
            self._text_result(
                [self._text_candidate(FIELD_DELIVERY_DATE, "2099-01-11")]
            ),
            self._layout_group(STOP_TYPE_DELIVERY, STOP_FIELD_DATE, "2099-01-12"),
            baseline_resolution_result={
                "field_statuses": {FIELD_DELIVERY_DATE: "resolved"},
            },
        )

        self.assertIn(FIELD_DELIVERY_DATE, result["conflict_stop_fields"])
        self.assertIn("stop_fusion_conflict:delivery_date", result["warning_codes"])

    def test_multi_stop_groups_are_preserved(self):
        pickup = build_stop_group_candidate(
            stop_group_id="pickup_group",
            stop_sequence=1,
            stop_type=STOP_TYPE_PICKUP,
            field_candidates=[
                build_stop_field_candidate(
                    stop_group_id="pickup_group",
                    stop_sequence=1,
                    stop_type=STOP_TYPE_PICKUP,
                    field_name=STOP_FIELD_LOCATION,
                    candidate_id="pickup_location",
                    confidence=0.9,
                )
            ],
        )
        delivery = build_stop_group_candidate(
            stop_group_id="delivery_group",
            stop_sequence=2,
            stop_type=STOP_TYPE_DELIVERY,
            field_candidates=[
                build_stop_field_candidate(
                    stop_group_id="delivery_group",
                    stop_sequence=2,
                    stop_type=STOP_TYPE_DELIVERY,
                    field_name=STOP_FIELD_LOCATION,
                    candidate_id="delivery_location",
                    confidence=0.9,
                )
            ],
        )

        result = fuse_stop_candidates(
            self._text_result([]),
            build_stop_association_result(stop_groups=[pickup, delivery]),
        )

        self.assertEqual(len(result["stop_groups"]), 2)

    def test_low_confidence_layout_and_text_routes_unchanged_not_worsened(self):
        result = fuse_stop_candidates(
            self._text_result(
                [
                    self._text_candidate(
                        FIELD_PICKUP_LOCATION,
                        "FAKE ORIGIN",
                        confidence=CANDIDATE_CONFIDENCE_LOW,
                    )
                ]
            ),
            self._layout_group(
                STOP_TYPE_PICKUP,
                STOP_FIELD_LOCATION,
                "FAKE ORIGIN",
                confidence=0.4,
            ),
            baseline_resolution_result={
                "field_statuses": {FIELD_PICKUP_LOCATION: "resolved"},
            },
        )

        self.assertEqual(result["worsened_fields"], [])
        self.assertIn(FIELD_PICKUP_LOCATION, result["unchanged_fields"])


if __name__ == "__main__":
    unittest.main()
