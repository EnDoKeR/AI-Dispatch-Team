import json
import unittest

from app.market_intelligence.case_event_normalizer import normalize_case_event
from tests.fixtures.normalized_event_wrapper_cases import (
    NORMALIZED_EVENT_WRAPPER_CASES,
)


class NormalizedEventWrapperCasesTest(unittest.TestCase):
    def test_fixtures_import(self):
        self.assertGreaterEqual(len(NORMALIZED_EVENT_WRAPPER_CASES), 8)

    def test_every_fixture_normalizes(self):
        for scenario in NORMALIZED_EVENT_WRAPPER_CASES:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                wrapper = normalize_case_event(scenario["event"])
                normalized = wrapper["normalized_payload"]

                self.assertEqual(
                    normalized["event_type"],
                    scenario["expected_event_type"],
                )

    def test_expected_event_group_matches(self):
        for scenario in NORMALIZED_EVENT_WRAPPER_CASES:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                wrapper = normalize_case_event(scenario["event"])

                self.assertEqual(
                    wrapper["normalized_payload"]["event_group"],
                    scenario["expected_event_group"],
                )

    def test_expected_warnings_match(self):
        for scenario in NORMALIZED_EVENT_WRAPPER_CASES:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                wrapper = normalize_case_event(scenario["event"])

                self.assertEqual(
                    sorted(wrapper["warnings"]),
                    sorted(scenario["expected_warnings"]),
                )

    def test_fixtures_are_json_serializable(self):
        json.dumps(NORMALIZED_EVENT_WRAPPER_CASES)

    def test_no_real_private_data(self):
        fixture_text = json.dumps(NORMALIZED_EVENT_WRAPPER_CASES).lower()

        blocked_terms = [
            "@",
            "gmail",
            "yahoo",
            "outlook",
            "phone",
            "contact",
            "private_ratecons",
            "mc#",
        ]

        for term in blocked_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, fixture_text)


if __name__ == "__main__":
    unittest.main()
