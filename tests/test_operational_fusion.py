import unittest

from app.document_ai.operational_fusion import (
    OPERATIONAL_FUSION_VERSION,
    fuse_operational_detail_candidates,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_COMMODITY,
    FIELD_EQUIPMENT,
    FIELD_SPECIAL_REQUIREMENT,
    FIELD_WEIGHT,
    SOURCE_REGEX,
    SOURCE_TABLE_PATTERN_FUTURE,
    build_field_candidate,
)


class OperationalFusionTests(unittest.TestCase):
    def _candidate(
        self,
        field_name,
        value,
        confidence=CANDIDATE_CONFIDENCE_HIGH,
        candidate_id="candidate",
        section_role="COMMODITY_WEIGHT",
        warnings=None,
        source=SOURCE_TABLE_PATTERN_FUTURE,
        value_type="",
    ):
        candidate = build_field_candidate(
            field_name=field_name,
            raw_value=value,
            normalized_value=value,
            confidence=confidence,
            source=source,
            candidate_id=candidate_id,
            warnings=warnings,
            value_type=value_type,
        )
        candidate["layout_section_role"] = section_role
        return candidate

    def test_weight_improved_from_layout_table(self):
        layout = self._candidate(FIELD_WEIGHT, "44000", candidate_id="layout_weight")

        result = fuse_operational_detail_candidates(
            layout_candidates=[layout],
            baseline_statuses={FIELD_WEIGHT: "missing"},
        )

        self.assertIn(FIELD_WEIGHT, result["improved_fields"])
        self.assertEqual(result["decisions"][0]["selected_candidate_id"], "layout_weight")

    def test_commodity_improved_from_layout_table(self):
        layout = self._candidate(FIELD_COMMODITY, "FAKE STEEL", candidate_id="layout_commodity")

        result = fuse_operational_detail_candidates(
            layout_candidates=[layout],
            baseline_statuses={FIELD_COMMODITY: "needs_review"},
        )

        self.assertIn(FIELD_COMMODITY, result["improved_fields"])

    def test_equipment_conflict_routes_review(self):
        text = self._candidate(
            FIELD_EQUIPMENT,
            "Van",
            candidate_id="text_equipment",
            source=SOURCE_REGEX,
            section_role="",
        )
        layout = self._candidate(
            FIELD_EQUIPMENT,
            "Flatbed",
            candidate_id="layout_equipment",
        )

        result = fuse_operational_detail_candidates(
            text_candidates=[text],
            layout_candidates=[layout],
            baseline_statuses={FIELD_EQUIPMENT: "resolved"},
        )

        self.assertIn(FIELD_EQUIPMENT, result["conflict_fields"])
        self.assertTrue(result["decisions"][0]["review_required"])
        self.assertEqual(result["worsened_fields"], [])
        self.assertIn(
            "layout_candidate_rejected_to_prevent_regression",
            result["warning_codes"],
        )

    def test_special_requirement_preserved(self):
        text = self._candidate(
            FIELD_SPECIAL_REQUIREMENT,
            "tracking_required",
            candidate_id="text_req",
            source=SOURCE_REGEX,
            section_role="",
        )
        layout = self._candidate(
            FIELD_SPECIAL_REQUIREMENT,
            "tracking_required",
            candidate_id="layout_req",
            section_role="SPECIAL_INSTRUCTIONS",
            value_type="tracking_required",
        )

        result = fuse_operational_detail_candidates(
            text_candidates=[text],
            layout_candidates=[layout],
            baseline_statuses={FIELD_SPECIAL_REQUIREMENT: "resolved"},
        )

        self.assertIn(FIELD_SPECIAL_REQUIREMENT, result["unchanged_fields"])
        self.assertEqual(result["worsened_fields"], [])

    def test_weak_legal_terms_requirement_lower_confidence_no_worsen(self):
        text = self._candidate(
            FIELD_SPECIAL_REQUIREMENT,
            "tracking_required",
            candidate_id="text_req",
            source=SOURCE_REGEX,
            section_role="",
        )
        legal = self._candidate(
            FIELD_SPECIAL_REQUIREMENT,
            "tracking_required",
            confidence=CANDIDATE_CONFIDENCE_LOW,
            candidate_id="legal_req",
            section_role="LEGAL_TERMS",
            warnings=["requirement_from_supplemental_terms"],
        )

        result = fuse_operational_detail_candidates(
            text_candidates=[text],
            layout_candidates=[legal],
            baseline_statuses={FIELD_SPECIAL_REQUIREMENT: "resolved"},
        )

        self.assertEqual(result["worsened_fields"], [])
        self.assertIn(FIELD_SPECIAL_REQUIREMENT, result["unchanged_fields"])

    def test_no_driver_compatibility_decision(self):
        result = fuse_operational_detail_candidates(
            layout_candidates=[
                self._candidate(
                    FIELD_SPECIAL_REQUIREMENT,
                    "no_touch",
                    candidate_id="no_touch",
                    section_role="SPECIAL_INSTRUCTIONS",
                )
            ],
            baseline_statuses={FIELD_SPECIAL_REQUIREMENT: "missing"},
        )

        text = str(result)
        self.assertEqual(result["fusion_version"], OPERATIONAL_FUSION_VERSION)
        self.assertNotIn("ACCEPT", text)
        self.assertNotIn("REJECT", text)
        self.assertNotIn("driver_compatible", text)


if __name__ == "__main__":
    unittest.main()
