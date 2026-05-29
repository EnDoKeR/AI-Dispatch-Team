import inspect
import unittest

from app.market_intelligence import case_event_types
from app.market_intelligence.case_event_types import (
    AI_DECISION_CREATED,
    CLEAN_EXIT_FOUND,
    DISPATCHER_FEEDBACK_ADDED,
    EVENT_GROUP_LOAD_LEVEL,
    EVENT_GROUP_RELOAD_WATCH,
    EVENT_GROUP_SEARCH_REPORTING,
    EVENT_GROUP_UNKNOWN,
    FACTORING_PACKET_READY,
    MARKET_SNAPSHOT_SENT,
    RATECON_RECEIVED,
    SEARCH_HEALTH_CHECK_SENT,
    TELEGRAM_ALERT_SENT,
    event_type_group,
    event_type_metadata,
    event_types_by_group,
    is_known_event_type,
    normalize_event_type,
)


class CaseEventTypesTest(unittest.TestCase):
    def test_important_existing_event_types_exist(self):
        self.assertEqual(AI_DECISION_CREATED, "AI_DECISION_CREATED")
        self.assertEqual(TELEGRAM_ALERT_SENT, "TELEGRAM_ALERT_SENT")
        self.assertEqual(DISPATCHER_FEEDBACK_ADDED, "DISPATCHER_FEEDBACK_ADDED")
        self.assertEqual(RATECON_RECEIVED, "RATECON_RECEIVED")

    def test_future_event_types_exist_but_are_not_wired(self):
        self.assertEqual(MARKET_SNAPSHOT_SENT, "MARKET_SNAPSHOT_SENT")
        self.assertEqual(SEARCH_HEALTH_CHECK_SENT, "SEARCH_HEALTH_CHECK_SENT")
        self.assertEqual(CLEAN_EXIT_FOUND, "CLEAN_EXIT_FOUND")
        self.assertEqual(FACTORING_PACKET_READY, "FACTORING_PACKET_READY")

    def test_normalize_event_type(self):
        self.assertEqual(normalize_event_type(" telegram-alert sent "), "TELEGRAM_ALERT_SENT")
        self.assertEqual(normalize_event_type("clean/exit-found"), "CLEAN_EXIT_FOUND")
        self.assertEqual(normalize_event_type(""), "")

    def test_validate_known_event_type(self):
        self.assertTrue(is_known_event_type("telegram alert sent"))
        self.assertTrue(is_known_event_type("RATECON_RECEIVED"))
        self.assertFalse(is_known_event_type("SOMETHING_NEW"))

    def test_group_lookup(self):
        self.assertEqual(event_type_group("AI_DECISION_CREATED"), EVENT_GROUP_LOAD_LEVEL)
        self.assertEqual(event_type_group("MARKET_SNAPSHOT_SENT"), EVENT_GROUP_SEARCH_REPORTING)
        self.assertEqual(event_type_group("CLEAN_EXIT_FOUND"), EVENT_GROUP_RELOAD_WATCH)

    def test_unknown_event_safe(self):
        self.assertEqual(event_type_group("unknown event"), EVENT_GROUP_UNKNOWN)
        self.assertEqual(
            event_type_metadata("unknown event"),
            {
                "event_type": "UNKNOWN_EVENT",
                "event_group": EVENT_GROUP_UNKNOWN,
                "known": False,
            },
        )

    def test_event_types_by_group_returns_copy(self):
        event_types = event_types_by_group(EVENT_GROUP_LOAD_LEVEL)
        event_types.append("MUTATED")

        self.assertNotIn("MUTATED", event_types_by_group(EVENT_GROUP_LOAD_LEVEL))
        self.assertIn(AI_DECISION_CREATED, event_types_by_group(EVENT_GROUP_LOAD_LEVEL))

    def test_no_forbidden_imports(self):
        source = inspect.getsource(case_event_types).lower()

        forbidden_terms = [
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "repository",
            "sqlite",
            "jsonl",
            "pypdf",
            "gspread",
            "googlemaps",
            "dat_api",
            "apscheduler",
            "threading",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
