import json
import unittest

from app.document_ai.broker_template_candidate_extraction import (
    extract_ratecon_candidates_with_template_context,
)
from app.document_ai.broker_template_matcher import (
    TEMPLATE_SELECTION_STATUS_CONFLICT,
    TEMPLATE_SELECTION_STATUS_MATCHED,
    TEMPLATE_SELECTION_STATUS_UNKNOWN,
)
from app.document_ai.broker_template_registry import BrokerTemplateRegistry
from app.document_ai.ratecon_candidates import FIELD_BROKER_MC, FIELD_BROKER_NAME
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
        self.assertIn("template_conflict_no_scoring_applied", result["warnings"])

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
