import json
import unittest

from app.document_ai.broker_template_matcher import (
    TEMPLATE_SELECTION_STATUS_CONFLICT,
    TEMPLATE_SELECTION_STATUS_MATCHED,
    TEMPLATE_SELECTION_STATUS_UNKNOWN,
    select_broker_template,
)
from app.document_ai.ratecon_candidate_extraction import extract_ratecon_candidates
from tests.fixtures.document_ai.broker_templates.fixture_loader import (
    load_all_template_fixtures,
)
from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    build_fixture_text_artifact,
)


class BrokerTemplateMatcherTests(unittest.TestCase):
    def _select(self, fixture_name):
        artifact = build_fixture_text_artifact(fixture_name)
        candidate_result = extract_ratecon_candidates(artifact)
        return select_broker_template(
            artifact,
            load_all_template_fixtures(),
            candidate_result=candidate_result,
        )

    def test_alpha_fixture_matches_alpha_template(self):
        result = self._select("alpha_freight_mock_ratecon.txt")

        self.assertEqual(result["status"], TEMPLATE_SELECTION_STATUS_MATCHED)
        self.assertEqual(result["selected_template_id"], "alpha_freight_mock_v1")

    def test_northstar_fixture_matches_northstar_template(self):
        result = self._select("northstar_logistics_mock_ratecon.txt")

        self.assertEqual(result["status"], TEMPLATE_SELECTION_STATUS_MATCHED)
        self.assertEqual(result["selected_template_id"], "northstar_logistics_mock_v1")

    def test_tablelane_fixture_matches_tablelane_template(self):
        result = self._select("tablelane_transport_mock_ratecon.txt")

        self.assertEqual(result["status"], TEMPLATE_SELECTION_STATUS_MATCHED)
        self.assertEqual(result["selected_template_id"], "tablelane_transport_mock_v1")

    def test_unknown_fixture_returns_unknown(self):
        result = self._select("unknown_broker_ratecon.txt")

        self.assertEqual(result["status"], TEMPLATE_SELECTION_STATUS_UNKNOWN)
        self.assertEqual(result["selected_template_id"], "")

    def test_conflict_fixture_returns_conflict(self):
        result = self._select("template_conflict_ratecon.txt")

        self.assertEqual(result["status"], TEMPLATE_SELECTION_STATUS_CONFLICT)
        self.assertEqual(result["selected_template_id"], "")
        self.assertIn("template_conflict", result["warnings"])

    def test_exclude_keyword_prevents_wrong_template(self):
        result = self._select("northstar_logistics_mock_ratecon.txt")
        alpha = [
            match
            for match in result["matches"]
            if match["template_id"] == "alpha_freight_mock_v1"
        ][0]

        self.assertIn("Northstar Logistics Mock", alpha["excluded_keywords"])
        self.assertIn("template_exclude_keyword_seen", alpha["warnings"])

    def test_matcher_does_not_emit_dispatch_recommendations_or_cases(self):
        result = self._select("alpha_freight_mock_ratecon.txt")
        text = json.dumps(result)

        for literal in ["ACCEPT", "REJECT", "DispatchCase"]:
            with self.subTest(literal=literal):
                self.assertNotIn(literal, text)


if __name__ == "__main__":
    unittest.main()
