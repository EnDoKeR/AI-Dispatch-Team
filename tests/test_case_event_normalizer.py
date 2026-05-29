import copy
import inspect
import json
import unittest

from app.market_intelligence import case_event_normalizer
from app.market_intelligence.case_event_normalizer import (
    WARNING_MISSING_CASE_ID,
    WARNING_MISSING_SOURCE,
    WARNING_MISSING_TIMESTAMP_UTC,
    WARNING_UNKNOWN_EVENT_TYPE,
    normalize_case_event,
)


def ai_decision_event():
    return {
        "event_id": "EVT-1",
        "event_type": "AI_DECISION_CREATED",
        "case_id": "CASE-1",
        "timestamp_utc": "2026-05-29T10:00:00Z",
        "source": "synthetic_test",
        "load_id": "LOAD-1",
        "reference_id": "REF-1",
        "driver_name": "Alex",
        "payload": {
            "decision": "MATCH",
            "category": "LOAD OPPORTUNITY",
        },
    }


def telegram_event():
    return {
        "event_id": "EVT-2",
        "event_type": "telegram alert sent",
        "case_id": "CASE-1",
        "timestamp_utc": "2026-05-29T10:05:00Z",
        "source": "telegram_outbox",
        "reference_id": "REF-1",
        "payload": {
            "message_type": "LOAD_OPPORTUNITY",
            "telegram_message_id": "777",
        },
    }


def feedback_event():
    return {
        "event_id": "EVT-3",
        "event_type": "DISPATCHER_FEEDBACK_ADDED",
        "case_id": "CASE-1",
        "timestamp_utc": "2026-05-29T10:10:00Z",
        "source": "manual_feedback",
        "driver_name": "Alex",
        "payload": {
            "dispatcher_feedback": "calling",
            "dispatcher_note": "Synthetic note.",
        },
    }


class CaseEventNormalizerTest(unittest.TestCase):
    def test_normalizes_ai_decision_created_like_event(self):
        wrapper = normalize_case_event(ai_decision_event())
        normalized = wrapper["normalized_payload"]

        self.assertEqual(normalized["event_type"], "AI_DECISION_CREATED")
        self.assertEqual(normalized["event_group"], "load_level")
        self.assertEqual(normalized["case_id"], "CASE-1")
        self.assertEqual(
            normalized["details"]["legacy_event_payload"]["decision"],
            "MATCH",
        )

    def test_normalizes_telegram_alert_sent_like_event(self):
        wrapper = normalize_case_event(telegram_event())
        normalized = wrapper["normalized_payload"]

        self.assertEqual(normalized["event_type"], "TELEGRAM_ALERT_SENT")
        self.assertEqual(normalized["event_group"], "load_level")
        self.assertEqual(
            normalized["related_ids"]["reference_id"],
            "REF-1",
        )

    def test_normalizes_dispatcher_feedback_added_like_event(self):
        wrapper = normalize_case_event(feedback_event())
        normalized = wrapper["normalized_payload"]

        self.assertEqual(normalized["event_type"], "DISPATCHER_FEEDBACK_ADDED")
        self.assertEqual(normalized["event_group"], "load_level")
        self.assertEqual(
            normalized["details"]["legacy_event_payload"]["dispatcher_feedback"],
            "calling",
        )

    def test_preserves_legacy_payload(self):
        event = ai_decision_event()

        wrapper = normalize_case_event(event)

        self.assertEqual(wrapper["legacy_payload"], event)
        self.assertIsNot(wrapper["legacy_payload"], event)

    def test_adds_event_group(self):
        wrapper = normalize_case_event({
            "event_type": "MARKET_SNAPSHOT_SENT",
            "case_id": "CASE-1",
            "timestamp_utc": "2026-05-29T10:00:00Z",
            "source": "dry_run",
        })

        self.assertEqual(
            wrapper["normalized_payload"]["event_group"],
            "search_reporting",
        )

    def test_missing_identity_fields_add_warnings(self):
        wrapper = normalize_case_event({"event_type": "AI_DECISION_CREATED"})

        self.assertEqual(
            wrapper["warnings"],
            [
                WARNING_MISSING_CASE_ID,
                WARNING_MISSING_TIMESTAMP_UTC,
                WARNING_MISSING_SOURCE,
            ],
        )

    def test_unknown_event_type_handled_safely(self):
        wrapper = normalize_case_event({
            "event_type": "future event",
            "case_id": "CASE-1",
            "timestamp_utc": "2026-05-29T10:00:00Z",
            "source": "synthetic_test",
        })

        self.assertEqual(wrapper["normalized_payload"]["event_type"], "FUTURE_EVENT")
        self.assertEqual(wrapper["normalized_payload"]["event_group"], "unknown")
        self.assertIn(WARNING_UNKNOWN_EVENT_TYPE, wrapper["warnings"])

    def test_wrapper_is_json_serializable(self):
        wrapper = normalize_case_event({
            "event_type": "AI_DECISION_CREATED",
            "case_id": "CASE-1",
            "timestamp_utc": "2026-05-29T10:00:00Z",
            "source": "synthetic_test",
            "payload": {"not_json": object()},
        })

        json.dumps(wrapper)

    def test_does_not_mutate_input(self):
        event = ai_decision_event()
        before = copy.deepcopy(event)

        wrapper = normalize_case_event(event)
        wrapper["legacy_payload"]["payload"]["decision"] = "BLOCK"
        wrapper["normalized_payload"]["details"]["legacy_event_payload"]["decision"] = "BLOCK"

        self.assertEqual(event, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(case_event_normalizer).lower()

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
