import json
import unittest

from app.market_intelligence.decision_engine.timeline_preview import (
    build_decision_result_timeline_preview,
)
from tests.fixtures.decision_result_timeline_previews import (
    DECISION_RESULT_TIMELINE_PREVIEWS,
)


class DecisionResultTimelinePreviewFixturesTest(unittest.TestCase):
    def test_fixtures_import(self):
        self.assertGreaterEqual(len(DECISION_RESULT_TIMELINE_PREVIEWS), 5)
        self.assertLessEqual(len(DECISION_RESULT_TIMELINE_PREVIEWS), 8)

    def test_every_fixture_builds_preview_payload(self):
        for fixture in DECISION_RESULT_TIMELINE_PREVIEWS:
            with self.subTest(fixture=fixture["scenario_id"]):
                preview = build_decision_result_timeline_preview(
                    fixture["decision_result"],
                    case_id=fixture["case_id"],
                    timestamp_utc=fixture["timestamp_utc"],
                    related_ids=fixture["related_ids"],
                )

                self.assertEqual(preview["event_type"], fixture["expected_event_type"])
                self.assertEqual(preview["case_id"], fixture["case_id"])

    def test_expected_decision_appears_in_payload(self):
        for fixture in DECISION_RESULT_TIMELINE_PREVIEWS:
            with self.subTest(fixture=fixture["scenario_id"]):
                preview = build_decision_result_timeline_preview(
                    fixture["decision_result"],
                    case_id=fixture["case_id"],
                )
                result = preview["details"]["decision_result"]

                self.assertEqual(result["decision"], fixture["expected_decision"])

    def test_expected_risk_flags_appear_in_payload(self):
        for fixture in DECISION_RESULT_TIMELINE_PREVIEWS:
            with self.subTest(fixture=fixture["scenario_id"]):
                preview = build_decision_result_timeline_preview(
                    fixture["decision_result"],
                    case_id=fixture["case_id"],
                )
                risk_flags = preview["details"]["decision_result"]["risk_flags"]

                for flag in fixture["expected_risk_flags"]:
                    self.assertIn(flag, risk_flags)

    def test_fixtures_are_json_serializable(self):
        json.dumps(DECISION_RESULT_TIMELINE_PREVIEWS)

    def test_no_real_private_data(self):
        serialized = json.dumps(DECISION_RESULT_TIMELINE_PREVIEWS).lower()

        real_data_terms = [
            "@",
            "gmail",
            "yahoo",
            "hotmail",
            "real broker",
            "real customer",
            "private",
            "555-",
            "mc#",
        ]

        for term in real_data_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, serialized)


if __name__ == "__main__":
    unittest.main()
