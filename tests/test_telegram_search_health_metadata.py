import inspect
import unittest

from app.market_intelligence import telegram_search_health_metadata
from app.market_intelligence.telegram_search_health_metadata import (
    build_search_health_metadata,
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


class TestTelegramSearchHealthMetadata(unittest.TestCase):
    def test_builds_core_search_health_metadata(self):
        metadata = build_search_health_metadata(search_request=FakeSearchRequest())

        self.assertEqual(metadata["message_type"], "SEARCH_HEALTH_CHECK")
        self.assertEqual(metadata["category"], "SEARCH HEALTH CHECK")
        self.assertEqual(metadata["driver_name"], "Alex")

    def test_load_specific_fields_are_intentionally_empty(self):
        metadata = build_search_health_metadata(
            search_request=FakeSearchRequest(),
            loads=[FakeLoad()],
            top_opportunities=[FakeLoad()],
            review_once_loads=[FakeLoad()],
        )

        self.assertEqual(metadata["pickup"], "")
        self.assertEqual(metadata["delivery"], "")
        self.assertEqual(metadata["rate"], "")
        self.assertEqual(metadata["broker"], "")
        self.assertEqual(metadata["broker_mc"], "")
        self.assertEqual(metadata["reference_id"], "")

    def test_search_fields_come_from_search_request(self):
        metadata = build_search_health_metadata(search_request=FakeSearchRequest())

        self.assertEqual(metadata["search_area"], "Dallas, TX")
        self.assertEqual(metadata["current_location"], "Dallas, TX")
        self.assertEqual(metadata["available_time"], "Now")
        self.assertEqual(metadata["equipment"], "Flatbed")
        self.assertEqual(metadata["target_direction"], "TX")

    def test_search_area_falls_back_to_search_area_field(self):
        search_request = FakeSearchRequest()
        search_request.current_location = ""
        search_request.search_area = "DFW"

        metadata = build_search_health_metadata(search_request=search_request)

        self.assertEqual(metadata["search_area"], "DFW")
        self.assertEqual(metadata["current_location"], "")

    def test_counts_and_status_fields_come_from_inputs(self):
        metadata = build_search_health_metadata(
            search_request=FakeSearchRequest(),
            loads=[FakeLoad(), FakeLoad(), FakeLoad()],
            top_opportunities=[FakeLoad()],
            review_once_loads=[FakeLoad(), FakeLoad()],
            monitored_minutes=45,
            qualified_loads=6,
            clean_matches=1,
            blocked_count=8,
            health_status="NO_CLEAN_MATCHES",
            action_status="REVIEW_FILTERS",
            reason="No clean matches found.",
        )

        self.assertEqual(metadata["monitored_minutes"], 45)
        self.assertEqual(metadata["total_loads"], 3)
        self.assertEqual(metadata["top_opportunities"], 1)
        self.assertEqual(metadata["review_once_count"], 2)
        self.assertEqual(metadata["qualified_loads"], 6)
        self.assertEqual(metadata["clean_matches"], 1)
        self.assertEqual(metadata["blocked_count"], 8)
        self.assertEqual(metadata["health_status"], "NO_CLEAN_MATCHES")
        self.assertEqual(metadata["action_status"], "REVIEW_FILTERS")
        self.assertEqual(metadata["reason"], "No clean matches found.")

    def test_clean_matches_defaults_to_top_opportunity_count(self):
        metadata = build_search_health_metadata(
            top_opportunities=[FakeLoad(), FakeLoad()],
        )

        self.assertEqual(metadata["clean_matches"], 2)

    def test_missing_inputs_are_safe_defaults(self):
        metadata = build_search_health_metadata()

        self.assertEqual(metadata["driver_name"], "")
        self.assertEqual(metadata["search_area"], "")
        self.assertEqual(metadata["current_location"], "")
        self.assertEqual(metadata["available_time"], "")
        self.assertEqual(metadata["equipment"], "")
        self.assertEqual(metadata["target_direction"], "")
        self.assertEqual(metadata["monitored_minutes"], 30)
        self.assertEqual(metadata["total_loads"], 0)
        self.assertEqual(metadata["top_opportunities"], 0)
        self.assertEqual(metadata["review_once_count"], 0)
        self.assertEqual(metadata["qualified_loads"], 0)
        self.assertEqual(metadata["clean_matches"], 0)
        self.assertEqual(metadata["blocked_count"], 0)
        self.assertEqual(metadata["health_status"], "")
        self.assertEqual(metadata["action_status"], "")
        self.assertEqual(metadata["reason"], "")

    def test_helper_does_not_mutate_inputs(self):
        loads = [FakeLoad()]
        top_opportunities = [FakeLoad()]
        review_once_loads = [FakeLoad()]
        search_request = FakeSearchRequest()

        loads_before = list(loads)
        top_before = list(top_opportunities)
        review_before = list(review_once_loads)
        search_request_before = dict(search_request.__dict__)

        build_search_health_metadata(
            search_request=search_request,
            loads=loads,
            top_opportunities=top_opportunities,
            review_once_loads=review_once_loads,
        )

        self.assertEqual(loads, loads_before)
        self.assertEqual(top_opportunities, top_before)
        self.assertEqual(review_once_loads, review_before)
        self.assertEqual(search_request.__dict__, search_request_before)

    def test_helper_does_not_import_sender_notifier_formatter_or_logger(self):
        source = inspect.getsource(telegram_search_health_metadata)

        self.assertNotIn("telegram_sender", source)
        self.assertNotIn("telegram_notifier", source)
        self.assertNotIn("telegram_search_health_formatter", source)
        self.assertNotIn("telegram_outbox_logger", source)
        self.assertNotIn("parse_", source)

    def test_metadata_contains_expected_key_set(self):
        metadata = build_search_health_metadata(search_request=FakeSearchRequest())

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
                "monitored_minutes",
                "total_loads",
                "qualified_loads",
                "clean_matches",
                "top_opportunities",
                "review_once_count",
                "blocked_count",
                "health_status",
                "action_status",
                "reason",
            },
        )


if __name__ == "__main__":
    unittest.main()
