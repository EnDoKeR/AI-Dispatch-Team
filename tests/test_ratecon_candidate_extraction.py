import json
import unittest

from app.document_ai.ratecon_candidate_extraction import extract_ratecon_candidates
from app.document_ai.ratecon_candidates import (
    FIELD_ACCESSORIAL_TERM,
    FIELD_BROKER_NAME,
    FIELD_COMMODITY,
    FIELD_DELIVERY_LOCATION,
    FIELD_EQUIPMENT,
    FIELD_PICKUP_LOCATION,
    FIELD_RATE,
    FIELD_WEIGHT,
)
from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    build_fixture_text_artifact,
)


class RateConCandidateExtractionTests(unittest.TestCase):
    def _fields(self, result):
        return {candidate["field_name"] for candidate in result["candidates"]}

    def test_simple_fixture_returns_candidates_across_multiple_fields(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")

        result = extract_ratecon_candidates(artifact)
        fields = self._fields(result)

        self.assertIn(FIELD_RATE, fields)
        self.assertIn(FIELD_BROKER_NAME, fields)
        self.assertIn(FIELD_PICKUP_LOCATION, fields)
        self.assertIn(FIELD_DELIVERY_LOCATION, fields)
        self.assertIn(FIELD_EQUIPMENT, fields)
        self.assertIn(FIELD_WEIGHT, fields)
        self.assertIn(FIELD_COMMODITY, fields)

    def test_multi_amount_fixture_preserves_multiple_money_candidates(self):
        artifact = build_fixture_text_artifact("multi_amount_ratecon.txt")

        result = extract_ratecon_candidates(artifact)
        money_candidates = [
            candidate
            for candidate in result["candidates"]
            if candidate["field_name"] in [FIELD_RATE, FIELD_ACCESSORIAL_TERM]
        ]

        self.assertGreaterEqual(len(money_candidates), 5)

    def test_missing_core_fixture_returns_missing_candidate_warnings(self):
        artifact = build_fixture_text_artifact("missing_core_fields_ratecon.txt")

        result = extract_ratecon_candidates(artifact)

        self.assertIn(FIELD_RATE, result["missing_candidate_fields"])
        self.assertIn(FIELD_PICKUP_LOCATION, self._fields(result))
        self.assertIn("no_money_candidates_found", result["warnings"])

    def test_orchestrator_output_serializes(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")

        result = extract_ratecon_candidates(artifact)

        json.dumps(result)

    def test_orchestrator_does_not_emit_dispatch_recommendations(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")
        text = str(extract_ratecon_candidates(artifact))

        for literal in ["ACCEPT", "REJECT", "DispatchCase"]:
            with self.subTest(literal=literal):
                self.assertNotIn(literal, text)


if __name__ == "__main__":
    unittest.main()
