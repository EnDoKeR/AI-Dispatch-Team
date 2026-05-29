import copy
import inspect
import json
import unittest

from app.market_intelligence import case_event_payload
from app.market_intelligence.case_event_payload import build_event_payload
from app.market_intelligence.case_event_types import (
    EVENT_GROUP_LOAD_LEVEL,
    EVENT_GROUP_RELOAD_WATCH,
    EVENT_GROUP_SEARCH_REPORTING,
    EVENT_GROUP_UNKNOWN,
)


class CaseEventPayloadTest(unittest.TestCase):
    def test_builds_basic_load_level_event_payload(self):
        payload = build_event_payload(
            "AI_DECISION_CREATED",
            case_id="CASE-1",
            timestamp_utc="2026-05-29T10:00:00Z",
            source="dry_run",
            details={"decision": "MATCH"},
            related_ids={"load_id": "LOAD-1"},
        )

        self.assertEqual(payload["event_type"], "AI_DECISION_CREATED")
        self.assertEqual(payload["event_group"], EVENT_GROUP_LOAD_LEVEL)
        self.assertEqual(payload["case_id"], "CASE-1")
        self.assertEqual(payload["details"], {"decision": "MATCH"})
        self.assertEqual(payload["related_ids"], {"load_id": "LOAD-1"})

    def test_builds_search_reporting_event_payload(self):
        payload = build_event_payload(
            "market snapshot sent",
            details={"driver_name": "Alex"},
        )

        self.assertEqual(payload["event_type"], "MARKET_SNAPSHOT_SENT")
        self.assertEqual(payload["event_group"], EVENT_GROUP_SEARCH_REPORTING)

    def test_builds_reload_watch_event_payload(self):
        payload = build_event_payload(
            "clean-exit-found",
            details={"best_exit_reference_id": "EXIT-1"},
        )

        self.assertEqual(payload["event_type"], "CLEAN_EXIT_FOUND")
        self.assertEqual(payload["event_group"], EVENT_GROUP_RELOAD_WATCH)

    def test_unknown_event_type_handled_safely(self):
        payload = build_event_payload("future event", details={"x": 1})

        self.assertEqual(payload["event_type"], "FUTURE_EVENT")
        self.assertEqual(payload["event_group"], EVENT_GROUP_UNKNOWN)
        self.assertEqual(payload["details"], {"x": 1})

    def test_safe_defaults(self):
        payload = build_event_payload("")

        self.assertEqual(payload["event_type"], "")
        self.assertEqual(payload["event_group"], EVENT_GROUP_UNKNOWN)
        self.assertEqual(payload["case_id"], "")
        self.assertEqual(payload["timestamp_utc"], "")
        self.assertEqual(payload["source"], "")
        self.assertEqual(payload["details"], {})
        self.assertEqual(payload["related_ids"], {})

    def test_payload_is_json_serializable(self):
        payload = build_event_payload(
            "AI_DECISION_CREATED",
            details={"tags": {"a", "b"}, "object": object()},
        )

        json.dumps(payload)

    def test_does_not_mutate_inputs(self):
        details = {"nested": {"decision": "MATCH"}}
        related_ids = {"load_id": "LOAD-1"}
        before_details = copy.deepcopy(details)
        before_related_ids = copy.deepcopy(related_ids)

        payload = build_event_payload(
            "AI_DECISION_CREATED",
            details=details,
            related_ids=related_ids,
        )
        payload["details"]["nested"]["decision"] = "BLOCK"
        payload["related_ids"]["load_id"] = "CHANGED"

        self.assertEqual(details, before_details)
        self.assertEqual(related_ids, before_related_ids)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(case_event_payload).lower()

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
