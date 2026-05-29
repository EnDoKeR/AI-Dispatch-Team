import copy
import inspect
import unittest

from app.market_intelligence import telegram_summary_metadata
from app.market_intelligence.telegram_summary_metadata import (
    build_market_summary_metadata,
)


class FakeLoad:
    pickup = "Dallas, TX"
    delivery = "Houston, TX"
    rate = 2200
    reference_id = "REF-123"


class FakeSearchRequest:
    driver_name = "Alex"
    current_location = "Dallas, TX"
    search_area = "Texas"
    available_time = "Now"
    equipment = "Flatbed"
    target_direction = "TX"


class TestTelegramSummaryMetadata(unittest.TestCase):
    def test_builds_core_market_snapshot_metadata(self):
        metadata = build_market_summary_metadata(
            stats={},
            recommendation={},
            top_opportunities=[],
            search_request=FakeSearchRequest(),
        )

        self.assertEqual(metadata["message_type"], "MARKET_SNAPSHOT")
        self.assertEqual(metadata["category"], "MARKET SNAPSHOT")
        self.assertEqual(metadata["driver_name"], "Alex")

    def test_load_specific_fields_are_intentionally_empty(self):
        metadata = build_market_summary_metadata(
            top_opportunities=[FakeLoad()],
            search_request=FakeSearchRequest(),
        )

        self.assertEqual(metadata["pickup"], "")
        self.assertEqual(metadata["delivery"], "")
        self.assertEqual(metadata["rate"], "")
        self.assertEqual(metadata["broker"], "")
        self.assertEqual(metadata["broker_mc"], "")
        self.assertEqual(metadata["reference_id"], "")

    def test_driver_and_search_fields_come_from_search_request(self):
        metadata = build_market_summary_metadata(search_request=FakeSearchRequest())

        self.assertEqual(metadata["driver_name"], "Alex")
        self.assertEqual(metadata["search_area"], "Dallas, TX")
        self.assertEqual(metadata["current_location"], "Dallas, TX")
        self.assertEqual(metadata["available_time"], "Now")
        self.assertEqual(metadata["equipment"], "Flatbed")
        self.assertEqual(metadata["target_direction"], "TX")

    def test_search_area_falls_back_to_search_area_field(self):
        search_request = FakeSearchRequest()
        search_request.current_location = ""
        search_request.search_area = "DFW"

        metadata = build_market_summary_metadata(search_request=search_request)

        self.assertEqual(metadata["search_area"], "DFW")
        self.assertEqual(metadata["current_location"], "")

    def test_recommendation_fields_populate_market_context(self):
        metadata = build_market_summary_metadata(
            recommendation={
                "market_activity": "MEDIUM",
                "driver_fit": "GOOD",
                "action_status": "SEND",
                "best_bucket": "400-700",
                "total_good_loads": 4,
                "total_qualified_loads": 7,
                "total_clean_matches": 3,
                "total_review_once": 2,
                "total_blocked": 5,
            },
            search_request=FakeSearchRequest(),
        )

        self.assertEqual(metadata["market_activity"], "MEDIUM")
        self.assertEqual(metadata["driver_fit"], "GOOD")
        self.assertEqual(metadata["action_status"], "SEND")
        self.assertEqual(metadata["best_bucket"], "400-700")
        self.assertEqual(metadata["good_loads"], 4)
        self.assertEqual(metadata["qualified_loads"], 7)
        self.assertEqual(metadata["clean_match_count"], 3)
        self.assertEqual(metadata["review_once_count"], 2)
        self.assertEqual(metadata["blocked_count"], 5)

    def test_stats_can_fill_market_activity_and_counts(self):
        metadata = build_market_summary_metadata(
            stats={
                "market_activity": "WEAK",
                "good_loads": 1,
                "qualified_loads": 2,
                "clean_match_count": 0,
                "review_once_count": 3,
                "blocked_count": 4,
            },
            recommendation={},
            search_request=FakeSearchRequest(),
        )

        self.assertEqual(metadata["market_activity"], "WEAK")
        self.assertEqual(metadata["good_loads"], 1)
        self.assertEqual(metadata["qualified_loads"], 2)
        self.assertEqual(metadata["clean_match_count"], 0)
        self.assertEqual(metadata["review_once_count"], 3)
        self.assertEqual(metadata["blocked_count"], 4)

    def test_count_fields_default_safely_to_zero(self):
        metadata = build_market_summary_metadata()

        self.assertEqual(metadata["good_loads"], 0)
        self.assertEqual(metadata["qualified_loads"], 0)
        self.assertEqual(metadata["clean_match_count"], 0)
        self.assertEqual(metadata["review_once_count"], 0)
        self.assertEqual(metadata["blocked_count"], 0)

    def test_top_opportunities_do_not_populate_load_core_fields(self):
        metadata = build_market_summary_metadata(
            recommendation={"best_bucket": "0-400"},
            top_opportunities=[FakeLoad()],
            search_request=FakeSearchRequest(),
        )

        self.assertEqual(metadata["pickup"], "")
        self.assertEqual(metadata["delivery"], "")
        self.assertEqual(metadata["rate"], "")
        self.assertEqual(metadata["reference_id"], "")
        self.assertEqual(metadata["best_bucket"], "0-400")

    def test_missing_inputs_are_safe_defaults(self):
        metadata = build_market_summary_metadata()

        self.assertEqual(metadata["driver_name"], "")
        self.assertEqual(metadata["search_area"], "")
        self.assertEqual(metadata["current_location"], "")
        self.assertEqual(metadata["available_time"], "")
        self.assertEqual(metadata["equipment"], "")
        self.assertEqual(metadata["target_direction"], "")
        self.assertEqual(metadata["market_activity"], "")
        self.assertEqual(metadata["driver_fit"], "")
        self.assertEqual(metadata["action_status"], "")
        self.assertEqual(metadata["best_bucket"], "")

    def test_helper_does_not_mutate_inputs(self):
        stats = {"market_activity": "GOOD", "good_loads": 3}
        recommendation = {"driver_fit": "GOOD", "best_bucket": "400-700"}
        top_opportunities = [FakeLoad()]
        search_request = FakeSearchRequest()

        stats_before = copy.deepcopy(stats)
        recommendation_before = copy.deepcopy(recommendation)
        top_opportunities_before = list(top_opportunities)
        search_request_before = dict(search_request.__dict__)

        build_market_summary_metadata(
            stats=stats,
            recommendation=recommendation,
            top_opportunities=top_opportunities,
            search_request=search_request,
        )

        self.assertEqual(stats, stats_before)
        self.assertEqual(recommendation, recommendation_before)
        self.assertEqual(top_opportunities, top_opportunities_before)
        self.assertEqual(search_request.__dict__, search_request_before)

    def test_helper_does_not_import_sender_notifier_formatter_or_logger(self):
        source = inspect.getsource(telegram_summary_metadata)

        self.assertNotIn("telegram_sender", source)
        self.assertNotIn("telegram_notifier", source)
        self.assertNotIn("telegram_market_summary_formatter", source)
        self.assertNotIn("telegram_outbox_logger", source)
        self.assertNotIn("parse_", source)

    def test_metadata_contains_expected_key_set(self):
        metadata = build_market_summary_metadata(
            stats={},
            recommendation={},
            top_opportunities=[FakeLoad()],
            search_request=FakeSearchRequest(),
        )

        self.assertEqual(
            set(metadata.keys()),
            {
                "message_type",
                "category",
                "driver_name",
                "pickup",
                "delivery",
                "rate",
                "broker",
                "broker_mc",
                "reference_id",
                "search_area",
                "current_location",
                "available_time",
                "equipment",
                "target_direction",
                "market_activity",
                "driver_fit",
                "action_status",
                "best_bucket",
                "good_loads",
                "qualified_loads",
                "clean_match_count",
                "review_once_count",
                "blocked_count",
            },
        )


if __name__ == "__main__":
    unittest.main()
