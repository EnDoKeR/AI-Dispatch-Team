import unittest

from app.document_ai.ratecon_candidate_generators import (
    build_operational_detail_candidate_result,
    generate_operational_detail_candidates,
)
from app.document_ai.ratecon_candidates import (
    FIELD_ACCESSORIAL_TERM,
    FIELD_COMMODITY,
    FIELD_EQUIPMENT,
    FIELD_SPECIAL_REQUIREMENT,
    FIELD_WEIGHT,
)
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates
from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    build_fixture_text_artifact,
)


class RateConOperationalDetailCandidatesTests(unittest.TestCase):
    def _field_candidates(self, candidates, field_name):
        return [
            candidate
            for candidate in candidates
            if candidate["field_name"] == field_name
        ]

    def test_equipment_candidate_from_clean_fixture(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")

        equipment = self._field_candidates(
            generate_operational_detail_candidates(artifact),
            FIELD_EQUIPMENT,
        )

        self.assertTrue(equipment)
        self.assertEqual(equipment[0]["raw_value"], "Conestoga 53 ft")
        self.assertIn("equipment_label", equipment[0]["confidence_reasons"])

    def test_special_requirement_candidates_from_flatbed_style_terms(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")

        requirements = self._field_candidates(
            generate_operational_detail_candidates(artifact),
            FIELD_SPECIAL_REQUIREMENT,
        )
        values = {candidate["normalized_value"] for candidate in requirements}

        self.assertIn("tarp required", values)
        self.assertIn("straps required", values)
        self.assertIn("no touch", values)

    def test_weight_candidate_normalizes_numeric_value(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")

        weight = self._field_candidates(
            generate_operational_detail_candidates(artifact),
            FIELD_WEIGHT,
        )

        self.assertTrue(weight)
        self.assertEqual(weight[0]["raw_value"], "42,500 lbs")
        self.assertEqual(weight[0]["normalized_value"], "42500")

    def test_commodity_candidate_from_label(self):
        artifact = build_fixture_text_artifact("ambiguous_references_ratecon.txt")

        commodity = self._field_candidates(
            generate_operational_detail_candidates(artifact),
            FIELD_COMMODITY,
        )

        self.assertTrue(commodity)
        self.assertEqual(commodity[0]["raw_value"], "FAKE PACKAGED GOODS")

    def test_accessorial_terms_are_candidates_not_final_rate_decisions(self):
        artifact = build_fixture_text_artifact("multi_amount_ratecon.txt")

        accessorial_terms = self._field_candidates(
            generate_operational_detail_candidates(artifact),
            FIELD_ACCESSORIAL_TERM,
        )

        self.assertGreaterEqual(len(accessorial_terms), 3)
        self.assertTrue(
            any("detention" in candidate["raw_value"].lower() for candidate in accessorial_terms)
        )

    def test_buried_special_requirements_from_notes_are_preserved(self):
        artifact = build_fixture_text_artifact("buried_special_requirements_ratecon.txt")

        requirements = self._field_candidates(
            generate_operational_detail_candidates(artifact),
            FIELD_SPECIAL_REQUIREMENT,
        )
        values = {candidate["normalized_value"] for candidate in requirements}

        self.assertIn("tarp required", values)
        self.assertIn("straps required", values)
        self.assertIn("chains required", values)
        self.assertIn("must call before pickup", values)
        self.assertIn("check in with pickup number", values)

    def test_missing_weight_is_not_invented(self):
        artifact = build_text_extraction_artifact_for_candidates(
            full_text=(
                "Equipment: Dry Van 53 ft\n"
                "Commodity: FAKE BOXES\n"
                "Special Requirements: no touch\n"
            ),
            source_name="missing_weight_fake.txt",
        )

        result = build_operational_detail_candidate_result(artifact)

        self.assertIn(FIELD_WEIGHT, result["missing_candidate_fields"])
        self.assertFalse(self._field_candidates(result["candidates"], FIELD_WEIGHT))

    def test_no_driver_compatibility_recommendation_emitted(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")
        result = build_operational_detail_candidate_result(artifact)
        text = str(result).lower()

        self.assertNotIn("driver_compatible", text)
        self.assertNotIn("dispatch_decision", text)


if __name__ == "__main__":
    unittest.main()
