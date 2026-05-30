import unittest

from app.document_ai.ratecon_candidate_extraction import extract_ratecon_candidates
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_RATE,
    FIELD_WEIGHT,
    build_candidate_extraction_result,
    build_field_candidate,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_CONFLICT,
    FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
    FIELD_RESOLUTION_STATUS_MISSING,
    FIELD_RESOLUTION_STATUS_RESOLVED,
    resolve_ratecon_fields,
)
from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    build_fixture_text_artifact,
)


class RateConFieldResolverTests(unittest.TestCase):
    def _resolution_by_field(self, result):
        return {
            resolution["field_name"]: resolution
            for resolution in result["resolutions"]
        }

    def test_simple_fixture_resolves_rate_and_basic_fields(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")
        candidate_result = extract_ratecon_candidates(artifact)

        result = resolve_ratecon_fields(candidate_result)
        resolutions = self._resolution_by_field(result)

        self.assertEqual(
            resolutions[FIELD_RATE]["status"],
            FIELD_RESOLUTION_STATUS_RESOLVED,
        )
        self.assertEqual(
            resolutions[FIELD_PICKUP_LOCATION]["status"],
            FIELD_RESOLUTION_STATUS_RESOLVED,
        )
        self.assertEqual(
            resolutions[FIELD_DELIVERY_LOCATION]["status"],
            FIELD_RESOLUTION_STATUS_RESOLVED,
        )
        self.assertEqual(
            resolutions[FIELD_WEIGHT]["selected_candidate"]["normalized_value"],
            "42500",
        )

    def test_multi_amount_fixture_resolves_carrier_pay_not_accessorials(self):
        artifact = build_fixture_text_artifact("multi_amount_ratecon.txt")
        candidate_result = extract_ratecon_candidates(artifact)

        result = resolve_ratecon_fields(candidate_result, field_names=[FIELD_RATE])
        rate_resolution = result["resolutions"][0]

        self.assertEqual(rate_resolution["status"], FIELD_RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(rate_resolution["selected_candidate"]["normalized_value"], "3100.00")

    def test_conflict_rate_fixture_marks_rate_conflict(self):
        artifact = build_fixture_text_artifact("conflict_rate_ratecon.txt")
        candidate_result = extract_ratecon_candidates(artifact)

        result = resolve_ratecon_fields(candidate_result, field_names=[FIELD_RATE])
        rate_resolution = result["resolutions"][0]

        self.assertEqual(rate_resolution["status"], FIELD_RESOLUTION_STATUS_CONFLICT)
        self.assertIn(FIELD_RATE, result["conflict_fields"])
        self.assertIn(FIELD_RATE, result["needs_check_fields"])

    def test_missing_core_fixture_marks_missing_fields(self):
        artifact = build_fixture_text_artifact("missing_core_fields_ratecon.txt")
        candidate_result = extract_ratecon_candidates(artifact)

        result = resolve_ratecon_fields(
            candidate_result,
            field_names=[
                FIELD_RATE,
                FIELD_PICKUP_DATE,
                FIELD_DELIVERY_DATE,
                FIELD_WEIGHT,
            ],
        )

        self.assertIn(FIELD_RATE, result["missing_fields"])
        self.assertIn(FIELD_PICKUP_DATE, result["missing_fields"])
        self.assertIn(FIELD_WEIGHT, result["missing_fields"])
        self.assertNotIn(FIELD_DELIVERY_DATE, result["missing_fields"])

    def test_low_confidence_candidate_marks_needs_check(self):
        candidate_result = build_candidate_extraction_result(
            candidates=[
                build_field_candidate(
                    field_name=FIELD_RATE,
                    raw_value="$2,850.00",
                    normalized_value="2850.00",
                    confidence=CANDIDATE_CONFIDENCE_LOW,
                )
            ],
        )

        result = resolve_ratecon_fields(candidate_result, field_names=[FIELD_RATE])
        rate_resolution = result["resolutions"][0]

        self.assertEqual(rate_resolution["status"], FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE)
        self.assertIn(FIELD_RATE, result["needs_check_fields"])

    def test_no_dispatch_case_or_recommendation_emitted(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")
        candidate_result = extract_ratecon_candidates(artifact)

        text = str(resolve_ratecon_fields(candidate_result))

        for literal in ["DispatchCase", "ACCEPT", "REJECT"]:
            with self.subTest(literal=literal):
                self.assertNotIn(literal, text)


if __name__ == "__main__":
    unittest.main()
