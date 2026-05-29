import json
import unittest

from app.market_intelligence.case_event_normalizer import normalize_case_event
from tests.fixtures.current_built_event_samples import CURRENT_BUILT_EVENT_SAMPLES


class CurrentBuiltEventSamplesTest(unittest.TestCase):
    def test_fixtures_import(self):
        self.assertEqual(len(CURRENT_BUILT_EVENT_SAMPLES), 9)

    def test_each_event_normalizes(self):
        for scenario in CURRENT_BUILT_EVENT_SAMPLES:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                wrapper = normalize_case_event(scenario["event"])

                self.assertEqual(
                    wrapper["normalized_payload"]["event_type"],
                    scenario["expected_event_type"],
                )

    def test_expected_event_groups_match(self):
        for scenario in CURRENT_BUILT_EVENT_SAMPLES:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                wrapper = normalize_case_event(scenario["event"])

                self.assertEqual(
                    wrapper["normalized_payload"]["event_group"],
                    scenario["expected_event_group"],
                )

    def test_expected_warnings_match(self):
        for scenario in CURRENT_BUILT_EVENT_SAMPLES:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                wrapper = normalize_case_event(scenario["event"])

                self.assertEqual(
                    sorted(wrapper["warnings"]),
                    sorted(scenario["expected_warnings"]),
                )

    def test_fixtures_json_serializable(self):
        json.dumps(CURRENT_BUILT_EVENT_SAMPLES)

    def test_no_real_private_data(self):
        fixture_text = json.dumps(CURRENT_BUILT_EVENT_SAMPLES).lower()
        blocked_terms = [
            "@",
            "gmail",
            "yahoo",
            "outlook",
            "private_ratecons",
            "real broker",
            "real customer",
            "real driver",
        ]

        for term in blocked_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, fixture_text)


if __name__ == "__main__":
    unittest.main()
