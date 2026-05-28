import unittest

from app.market_intelligence.driver_lane_preference_groups import (
    build_empty_lane_group,
    build_lane_groups,
    get_row_value,
)


class FakeRow(dict):
    def __getitem__(self, key):
        return dict.__getitem__(self, key)


class DriverLanePreferenceGroupsTest(unittest.TestCase):
    def test_get_row_value_handles_missing_and_none_values(self):
        row = FakeRow({"driver_name": "Alex", "pickup": None})

        self.assertEqual(get_row_value(row, "driver_name"), "Alex")
        self.assertEqual(get_row_value(row, "pickup", "UNKNOWN"), "UNKNOWN")
        self.assertEqual(get_row_value(row, "missing", "DEFAULT"), "DEFAULT")

    def test_build_empty_lane_group_has_expected_defaults(self):
        group = build_empty_lane_group("Alex", "Dallas, TX", "Houston, TX")

        self.assertEqual(group["driver_name"], "Alex")
        self.assertEqual(group["pickup"], "Dallas, TX")
        self.assertEqual(group["delivery"], "Houston, TX")
        self.assertEqual(group["feedback_counts"], {})
        self.assertEqual(group["case_count"], 0)
        self.assertEqual(group["latest_feedback"], "")
        self.assertEqual(group["booked_cases"], 0)
        self.assertEqual(group["rate_check_cases"], 0)

    def test_build_lane_groups_aggregates_same_lane_rows(self):
        rows = [
            FakeRow(
                {
                    "driver_name": "Alex",
                    "pickup": "Dallas, TX",
                    "delivery": "Houston, TX",
                    "feedback": "booked",
                    "feedback_count": 2,
                    "case_count": 2,
                    "avg_rate": 1200,
                    "avg_total_miles": 250,
                    "avg_total_rpm": 4.8,
                    "avg_weight": 40000,
                    "booked_cases": 2,
                    "ratecon_received_cases": 0,
                    "sent_to_driver_cases": 1,
                    "rejected_cases": 0,
                    "skipped_cases": 0,
                    "covered_cases": 0,
                    "final_booked": 1,
                    "final_ratecon_received": 0,
                    "final_rejected": 0,
                    "final_skipped": 0,
                    "final_covered": 0,
                    "match_cases": 2,
                    "review_once_cases": 0,
                    "blocked_cases": 0,
                    "load_opportunity_cases": 2,
                    "rate_check_cases": 0,
                    "broker_review_cases": 0,
                    "latest_feedback": "2026-01-01T10:00:00Z",
                }
            ),
            FakeRow(
                {
                    "driver_name": "Alex",
                    "pickup": "Dallas, TX",
                    "delivery": "Houston, TX",
                    "feedback": "rate_too_low",
                    "feedback_count": 1,
                    "case_count": 1,
                    "avg_rate": 900,
                    "avg_total_miles": 250,
                    "avg_total_rpm": 3.6,
                    "avg_weight": None,
                    "booked_cases": 0,
                    "ratecon_received_cases": 0,
                    "sent_to_driver_cases": 0,
                    "rejected_cases": 1,
                    "skipped_cases": 0,
                    "covered_cases": 0,
                    "final_booked": 0,
                    "final_ratecon_received": 0,
                    "final_rejected": 1,
                    "final_skipped": 0,
                    "final_covered": 0,
                    "match_cases": 0,
                    "review_once_cases": 1,
                    "blocked_cases": 0,
                    "load_opportunity_cases": 0,
                    "rate_check_cases": 1,
                    "broker_review_cases": 0,
                    "latest_feedback": "2026-01-02T10:00:00Z",
                }
            ),
        ]

        groups = build_lane_groups(rows)

        self.assertEqual(len(groups), 1)

        group = groups[0]

        self.assertEqual(group["driver_name"], "Alex")
        self.assertEqual(group["pickup"], "Dallas, TX")
        self.assertEqual(group["delivery"], "Houston, TX")
        self.assertEqual(group["feedback_counts"], {"booked": 2, "rate_too_low": 1})
        self.assertEqual(group["case_count"], 3)
        self.assertEqual(group["avg_rate_values"], [1200, 900])
        self.assertEqual(group["avg_miles_values"], [250, 250])
        self.assertEqual(group["avg_rpm_values"], [4.8, 3.6])
        self.assertEqual(group["avg_weight_values"], [40000])
        self.assertEqual(group["booked_cases"], 2)
        self.assertEqual(group["rejected_cases"], 1)
        self.assertEqual(group["match_cases"], 2)
        self.assertEqual(group["review_once_cases"], 1)
        self.assertEqual(group["load_opportunity_cases"], 2)
        self.assertEqual(group["rate_check_cases"], 1)
        self.assertEqual(group["latest_feedback"], "2026-01-02T10:00:00Z")

    def test_build_lane_groups_creates_separate_groups_for_different_lanes(self):
        rows = [
            FakeRow(
                {
                    "driver_name": "Alex",
                    "pickup": "Dallas, TX",
                    "delivery": "Houston, TX",
                    "feedback": "booked",
                    "feedback_count": 1,
                    "case_count": 1,
                    "latest_feedback": "2026-01-01T10:00:00Z",
                }
            ),
            FakeRow(
                {
                    "driver_name": "Alex",
                    "pickup": "Austin, TX",
                    "delivery": "Houston, TX",
                    "feedback": "booked",
                    "feedback_count": 1,
                    "case_count": 1,
                    "latest_feedback": "2026-01-01T10:00:00Z",
                }
            ),
        ]

        groups = build_lane_groups(rows)

        self.assertEqual(len(groups), 2)


if __name__ == "__main__":
    unittest.main()
