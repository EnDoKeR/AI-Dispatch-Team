import json
import unittest

from app.document_ai.broker_template_candidate_extraction import (
    TRUSTED_TEMPLATE_SCORING_CONFIDENCE,
    extract_ratecon_candidates_with_template_context,
)
from app.document_ai.broker_template_matcher import (
    TEMPLATE_SELECTION_STATUS_CONFLICT,
    TEMPLATE_SELECTION_STATUS_LOW_CONFIDENCE,
    TEMPLATE_SELECTION_STATUS_MATCHED,
    TEMPLATE_SELECTION_STATUS_UNKNOWN,
)
from app.document_ai.broker_templates import build_broker_template
from app.document_ai.broker_template_registry import BrokerTemplateRegistry
from app.document_ai.ratecon_candidates import FIELD_BROKER_MC, FIELD_BROKER_NAME
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates
from tests.fixtures.document_ai.broker_templates.fixture_loader import FIXTURE_DIR
from tests.fixtures.document_ai.ratecon_text.fixture_loader import build_fixture_text_artifact


class BrokerTemplateCandidateExtractionTests(unittest.TestCase):
    def setUp(self):
        self.registry = BrokerTemplateRegistry.from_directory(FIXTURE_DIR)

    def _extract(self, fixture_name):
        artifact = build_fixture_text_artifact(fixture_name)
        return extract_ratecon_candidates_with_template_context(artifact, self.registry)

    def test_alpha_fixture_gets_selected_template_and_boosts(self):
        result = self._extract("alpha_freight_mock_ratecon.txt")

        self.assertEqual(
            result["template_selection_result"]["status"],
            TEMPLATE_SELECTION_STATUS_MATCHED,
        )
        self.assertEqual(
            result["template_selection_result"]["selected_template_id"],
            "alpha_freight_mock_v1",
        )
        self.assertTrue(result["scoring_adjustments"])

    def test_northstar_fixture_gets_selected_template_and_boosts(self):
        result = self._extract("northstar_logistics_mock_ratecon.txt")

        self.assertEqual(
            result["template_selection_result"]["selected_template_id"],
            "northstar_logistics_mock_v1",
        )
        self.assertTrue(result["scoring_adjustments"])

    def test_unknown_fixture_remains_generic(self):
        result = self._extract("unknown_broker_ratecon.txt")

        self.assertEqual(
            result["template_selection_result"]["status"],
            TEMPLATE_SELECTION_STATUS_UNKNOWN,
        )
        self.assertEqual(result["scoring_adjustments"], [])
        self.assertEqual(
            result["base_candidate_result"]["candidates"],
            result["adjusted_candidate_result"]["candidates"],
        )

    def test_conflict_fixture_does_not_apply_scoring(self):
        result = self._extract("template_conflict_ratecon.txt")

        self.assertEqual(
            result["template_selection_result"]["status"],
            TEMPLATE_SELECTION_STATUS_CONFLICT,
        )
        self.assertEqual(result["scoring_adjustments"], [])
        self.assertFalse(result["template_scoring_applied"])
        self.assertTrue(result["template_context_limited"])
        self.assertIn("template_conflict_no_scoring_applied", result["warnings"])

    def test_matched_below_trusted_threshold_does_not_apply_scoring(self):
        weak_matched_template = build_broker_template(
            {
                "template_id": "weak_matched_mock_v1",
                "broker_key": "weak_matched_mock",
                "display_name": "Weak Matched Mock",
                "version": "1",
                "created_for_testing": True,
                "match_rules": [
                    {
                        "keywords": ["Weak Matched Mock"],
                        "confidence_boost": 0.26,
                    }
                ],
                "field_label_rules": [
                    {
                        "field_name": "rate",
                        "labels": ["Carrier Pay"],
                        "confidence_boost": 0.25,
                    }
                ],
            }
        )
        artifact = build_text_extraction_artifact_for_candidates(
            full_text="Weak Matched Mock\nCarrier Pay: $2,850.00\n",
            source_name="weak_matched_mock_fake.txt",
        )
        result = extract_ratecon_candidates_with_template_context(
            artifact,
            BrokerTemplateRegistry([weak_matched_template]),
        )

        self.assertEqual(
            result["template_selection_result"]["status"],
            TEMPLATE_SELECTION_STATUS_MATCHED,
        )
        self.assertLess(
            result["template_selection_result"]["selected_confidence"],
            TRUSTED_TEMPLATE_SCORING_CONFIDENCE,
        )
        self.assertFalse(result["template_scoring_applied"])
        self.assertTrue(result["template_context_limited"])
        self.assertEqual(result["scoring_adjustments"], [])
        self.assertEqual(
            result["base_candidate_result"]["candidates"],
            result["adjusted_candidate_result"]["candidates"],
        )
        self.assertIn(
            "template_match_below_trusted_scoring_threshold",
            result["warnings"],
        )

    def test_low_confidence_template_selection_does_not_apply_scoring(self):
        weak_template = build_broker_template(
            {
                "template_id": "weak_low_confidence_mock_v1",
                "broker_key": "weak_low_confidence_mock",
                "display_name": "Weak Low Confidence Mock",
                "version": "1",
                "created_for_testing": True,
                "match_rules": [
                    {
                        "keywords": ["Weak Low Confidence Mock"],
                        "confidence_boost": 0.05,
                    }
                ],
                "field_label_rules": [
                    {
                        "field_name": "rate",
                        "labels": ["Carrier Pay"],
                        "confidence_boost": 0.25,
                    }
                ],
            }
        )
        artifact = build_text_extraction_artifact_for_candidates(
            full_text="Weak Low Confidence Mock\nCarrier Pay: $2,850.00\n",
            source_name="weak_low_confidence_mock_fake.txt",
        )
        result = extract_ratecon_candidates_with_template_context(
            artifact,
            BrokerTemplateRegistry([weak_template]),
        )

        self.assertEqual(
            result["template_selection_result"]["status"],
            TEMPLATE_SELECTION_STATUS_LOW_CONFIDENCE,
        )
        self.assertFalse(result["template_scoring_applied"])
        self.assertTrue(result["template_context_limited"])
        self.assertEqual(result["scoring_adjustments"], [])

    def test_header_only_template_identity_adds_broker_name_candidate(self):
        result = self._extract("missing_broker_mc_header_only_ratecon.txt")
        candidates = result["adjusted_candidate_result"]["candidates"]
        broker_names = [
            candidate
            for candidate in candidates
            if candidate["field_name"] == FIELD_BROKER_NAME
        ]
        broker_mcs = [
            candidate
            for candidate in candidates
            if candidate["field_name"] == FIELD_BROKER_MC
        ]

        self.assertTrue(broker_names)
        self.assertEqual(broker_names[0]["normalized_value"], "Alpha Freight Mock")
        self.assertIn(
            "broker_name_from_template_header",
            broker_names[0]["confidence_reasons"],
        )
        self.assertEqual(broker_mcs, [])

    def test_output_serializes(self):
        result = self._extract("alpha_freight_mock_ratecon.txt")

        json.dumps(result)

    def test_no_dispatch_recommendation_or_case_output(self):
        result = self._extract("alpha_freight_mock_ratecon.txt")
        text = json.dumps(result)

        for literal in ["ACCEPT", "REJECT", "DispatchCase"]:
            with self.subTest(literal=literal):
                self.assertNotIn(literal, text)


if __name__ == "__main__":
    unittest.main()
