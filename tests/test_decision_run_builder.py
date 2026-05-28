import unittest

from app.market_intelligence.decision_run_builder import (
    build_decision_run_record,
    build_run_id,
    count_decisions,
)


class FakeSearchRequest:
    driver_name = "Alex"
    current_location = "Dallas, TX"
    equipment = "Flatbed"
    target_direction = "TX"


class TestDecisionRunBuilder(unittest.TestCase):
    def test_build_run_id_is_stable_for_same_inputs(self):
        first = build_run_id(
            search_request=FakeSearchRequest(),
            loads_count=3,
            timestamp_utc="2026-05-28T10:00:00+00:00",
        )
        second = build_run_id(
            search_request=FakeSearchRequest(),
            loads_count=3,
            timestamp_utc="2026-05-28T10:00:00+00:00",
        )

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("RUN-"))
        self.assertEqual(len(first), len("RUN-") + 12)

    def test_count_decisions_counts_match_review_once_and_block(self):
        decision_records = [
            {"decision": "MATCH"},
            {"decision": "MATCH"},
            {"decision": "REVIEW_ONCE"},
            {"decision": "BLOCK"},
            {"decision": "UNKNOWN"},
        ]

        counts = count_decisions(decision_records)

        self.assertEqual(
            counts,
            {
                "match_count": 2,
                "review_once_count": 1,
                "block_count": 1,
            },
        )

    def test_build_decision_run_record_builds_summary(self):
        decision_records = [
            {"decision": "MATCH"},
            {"decision": "REVIEW_ONCE"},
            {"decision": "BLOCK"},
        ]
        recommendation = {
            "market_activity": "MEDIUM",
            "driver_fit": "WORKABLE",
            "action_status": "SOME_MATCHES_AVAILABLE",
        }

        run_record = build_decision_run_record(
            search_request=FakeSearchRequest(),
            run_id="RUN-123",
            decision_records=decision_records,
            timestamp_utc="2026-05-28T10:00:00+00:00",
            recommendation=recommendation,
        )

        self.assertEqual(run_record["timestamp_utc"], "2026-05-28T10:00:00+00:00")
        self.assertEqual(run_record["run_id"], "RUN-123")
        self.assertEqual(run_record["driver_name"], "Alex")
        self.assertEqual(run_record["driver_location"], "Dallas, TX")
        self.assertEqual(run_record["driver_equipment"], "Flatbed")
        self.assertEqual(run_record["target_direction"], "TX")
        self.assertEqual(run_record["loads_analyzed"], 3)
        self.assertEqual(run_record["match_count"], 1)
        self.assertEqual(run_record["review_once_count"], 1)
        self.assertEqual(run_record["block_count"], 1)
        self.assertEqual(run_record["market_activity"], "MEDIUM")
        self.assertEqual(run_record["market_driver_fit"], "WORKABLE")
        self.assertEqual(run_record["market_action_status"], "SOME_MATCHES_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
