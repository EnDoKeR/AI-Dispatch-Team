import json
import unittest

from app.document_ai.broker_template_scoring import apply_template_candidate_scoring
from app.document_ai.ratecon_candidate_extraction import extract_ratecon_candidates
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    FIELD_ACCESSORIAL_TERM,
    FIELD_RATE,
)
from tests.fixtures.document_ai.broker_templates.fixture_loader import load_template_fixture
from tests.fixtures.document_ai.ratecon_text.fixture_loader import build_fixture_text_artifact


class BrokerTemplateScoringTests(unittest.TestCase):
    def _score_fixture(self, fixture_name, template_name):
        artifact = build_fixture_text_artifact(fixture_name)
        candidate_result = extract_ratecon_candidates(artifact)
        template = load_template_fixture(template_name)
        return apply_template_candidate_scoring(candidate_result, template)

    def test_alpha_carrier_pay_rate_candidate_is_boosted(self):
        result = self._score_fixture(
            "alpha_freight_mock_ratecon.txt",
            "alpha_freight_mock_v1.json",
        )
        rate_adjustments = [
            adjustment
            for adjustment in result["adjustments"]
            if adjustment["field_name"] == FIELD_RATE
        ]

        self.assertTrue(rate_adjustments)
        self.assertTrue(any(adjustment["delta"] > 0 for adjustment in rate_adjustments))
        self.assertEqual(rate_adjustments[0]["adjusted_confidence"], CANDIDATE_CONFIDENCE_HIGH)

    def test_accessorial_amount_near_detention_is_not_boosted_as_main_rate(self):
        result = self._score_fixture(
            "multi_amount_ratecon.txt",
            "alpha_freight_mock_v1.json",
        )
        accessorial_candidates = [
            candidate
            for candidate in result["adjusted_candidates"]
            if candidate["field_name"] == FIELD_ACCESSORIAL_TERM
        ]

        self.assertTrue(accessorial_candidates)
        self.assertFalse(
            any(candidate["field_name"] == FIELD_RATE and "detention" in str(candidate).lower()
                for candidate in result["adjusted_candidates"])
        )

    def test_northstar_agreed_amount_is_boosted(self):
        result = self._score_fixture(
            "northstar_logistics_mock_ratecon.txt",
            "northstar_logistics_mock_v1.json",
        )

        self.assertTrue(
            any("Agreed Amount" in " ".join(adjustment["reasons"]) for adjustment in result["adjustments"])
        )

    def test_tablelane_total_carrier_rate_is_boosted(self):
        result = self._score_fixture(
            "tablelane_transport_mock_ratecon.txt",
            "tablelane_transport_mock_v1.json",
        )

        self.assertTrue(
            any("Total Carrier Rate" in " ".join(adjustment["reasons"]) for adjustment in result["adjustments"])
        )

    def test_unknown_template_does_not_apply_boosts(self):
        artifact = build_fixture_text_artifact("alpha_freight_mock_ratecon.txt")
        candidate_result = extract_ratecon_candidates(artifact)

        result = apply_template_candidate_scoring(candidate_result, {})

        self.assertEqual(result["adjustments"], [])
        self.assertIn("no_template_for_scoring", result["warnings"])
        self.assertEqual(len(result["adjusted_candidates"]), len(candidate_result["candidates"]))

    def test_adjusted_scores_remain_between_zero_and_one(self):
        result = self._score_fixture(
            "alpha_freight_mock_ratecon.txt",
            "alpha_freight_mock_v1.json",
        )

        for adjustment in result["adjustments"]:
            with self.subTest(adjustment=adjustment["candidate_id"]):
                self.assertGreaterEqual(adjustment["adjusted_score"], 0.0)
                self.assertLessEqual(adjustment["adjusted_score"], 1.0)

    def test_scoring_result_serializes(self):
        result = self._score_fixture(
            "alpha_freight_mock_ratecon.txt",
            "alpha_freight_mock_v1.json",
        )

        json.dumps(result)


if __name__ == "__main__":
    unittest.main()
