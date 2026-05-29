import json
import unittest

from app.market_intelligence.intake.case_link_candidate import (
    build_intake_case_link_candidate,
)
from tests.fixtures.intake_case_link_candidates import (
    INTAKE_CASE_LINK_CANDIDATE_SCENARIOS,
)


def walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from walk_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from walk_strings(item)


class TestIntakeCaseLinkCandidateFixtures(unittest.TestCase):
    def test_fixtures_import(self):
        self.assertGreaterEqual(len(INTAKE_CASE_LINK_CANDIDATE_SCENARIOS), 10)

    def test_each_fixture_builds_expected_candidate(self):
        for scenario in INTAKE_CASE_LINK_CANDIDATE_SCENARIOS:
            with self.subTest(scenario=scenario["scenario_id"]):
                candidate = build_intake_case_link_candidate(
                    scenario["intake_record"],
                    scenario.get("case_record"),
                )

                self.assertEqual(
                    candidate["recommended_action"],
                    scenario["expected_recommended_action"],
                )
                self.assertEqual(
                    candidate["approval_required"],
                    scenario["expected_approval_required"],
                )

                for reason in scenario["expected_match_reasons"]:
                    self.assertIn(reason, candidate["match_reasons"])

                for reason in scenario["expected_mismatch_reasons"]:
                    self.assertIn(reason, candidate["mismatch_reasons"])

    def test_fixture_candidates_are_json_serializable(self):
        candidates = [
            build_intake_case_link_candidate(
                scenario["intake_record"],
                scenario.get("case_record"),
            )
            for scenario in INTAKE_CASE_LINK_CANDIDATE_SCENARIOS
        ]

        json.dumps(candidates)

    def test_fixtures_are_json_serializable(self):
        json.dumps(INTAKE_CASE_LINK_CANDIDATE_SCENARIOS)

    def test_fixtures_contain_no_real_private_data_markers(self):
        forbidden = [
            "@",
            "gmail",
            "yahoo",
            "outlook",
            "555-",
            "real broker",
            "real customer",
            "private ratecon",
        ]

        for scenario in INTAKE_CASE_LINK_CANDIDATE_SCENARIOS:
            with self.subTest(scenario=scenario["scenario_id"]):
                for text in walk_strings(scenario):
                    lowered = text.lower()
                    for marker in forbidden:
                        self.assertNotIn(marker, lowered)


if __name__ == "__main__":
    unittest.main()
