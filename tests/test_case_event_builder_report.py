import copy
import inspect
import json
import unittest

from app.market_intelligence import case_event_builder_report
from app.market_intelligence.case_event_builder import (
    build_ai_decision_created_event,
    build_dispatcher_feedback_added_event,
    build_telegram_alert_sent_event,
)
from app.market_intelligence.case_event_builder_report import (
    build_case_event_builder_shape_report,
)


def sample_case():
    return {
        "driver_name": "Alex",
        "load_id": "LOAD-123",
        "reference_id": "REF-123",
    }


def ai_decision_event():
    return build_ai_decision_created_event(
        case_id="CASE-123",
        case_record=sample_case(),
        decision_record={
            "timestamp_utc": "2026-05-28T10:00:00+00:00",
            "decision": "MATCH",
            "category": "LOAD OPPORTUNITY",
            "score": 90,
            "reasons": ["clean fit"],
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "rate": 3200,
        },
    )


def telegram_event():
    return build_telegram_alert_sent_event(
        case_id="CASE-123",
        case_record=sample_case(),
        outbox_record={
            "timestamp_utc": "2026-05-28T10:05:00+00:00",
            "message_type": "LOAD_OPPORTUNITY",
            "category": "LOAD OPPORTUNITY",
            "telegram_message_id": "777",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "rate": 3200,
            "broker": "Test Broker",
            "broker_mc": "123456",
            "reference_id": "REF-123",
        },
    )


def feedback_event():
    return build_dispatcher_feedback_added_event(
        case_id="CASE-123",
        case_record=sample_case(),
        feedback_record={
            "timestamp_utc": "2026-05-28T10:10:00+00:00",
            "source": "dispatcher_feedback",
            "dispatcher_feedback": "calling",
            "dispatcher_note": "Synthetic feedback.",
            "document_path": "",
        },
    )


class CaseEventBuilderReportTest(unittest.TestCase):
    def test_reports_shape_for_ai_decision_event(self):
        report = build_case_event_builder_shape_report([ai_decision_event()])

        self.assertEqual(report["total_events"], 1)
        self.assertEqual(report["event_types"], ["AI_DECISION_CREATED"])
        self.assertIn("payload", report["keys_by_event_type"]["AI_DECISION_CREATED"])
        self.assertEqual(report["event_group_summary"]["load_level"], 1)

    def test_reports_shape_for_telegram_alert_event(self):
        report = build_case_event_builder_shape_report([telegram_event()])

        self.assertEqual(report["event_types"], ["TELEGRAM_ALERT_SENT"])
        self.assertIn("event_id", report["keys_by_event_type"]["TELEGRAM_ALERT_SENT"])
        self.assertIn("payload", report["keys_by_event_type"]["TELEGRAM_ALERT_SENT"])

    def test_reports_shape_for_feedback_event(self):
        report = build_case_event_builder_shape_report([feedback_event()])

        self.assertEqual(report["event_types"], ["DISPATCHER_FEEDBACK_ADDED"])
        self.assertIn(
            "driver_name",
            report["keys_by_event_type"]["DISPATCHER_FEEDBACK_ADDED"],
        )

    def test_reports_missing_base_keys_safely(self):
        report = build_case_event_builder_shape_report([ai_decision_event()])
        missing = report["missing_base_keys_by_event_type"]["AI_DECISION_CREATED"]

        self.assertIn("event_group", missing)
        self.assertIn("details", missing)
        self.assertIn("related_ids", missing)
        self.assertNotIn("event_type", missing)
        self.assertNotIn("case_id", missing)

    def test_identifies_unknown_event_types(self):
        report = build_case_event_builder_shape_report([
            {"event_type": "UNPLANNED_EVENT", "case_id": "CASE-1"}
        ])

        self.assertEqual(report["unknown_event_types"], ["UNPLANNED_EVENT"])
        self.assertEqual(report["event_group_summary"]["unknown"], 1)

    def test_json_serializable_status(self):
        report = build_case_event_builder_shape_report([
            ai_decision_event(),
            {"event_type": "AI_DECISION_CREATED", "payload": {"bad": object()}},
        ])

        self.assertFalse(report["json_serializable"])
        self.assertEqual(report["non_serializable_event_indexes"], [1])
        json.dumps(report)

    def test_does_not_mutate_inputs(self):
        events = [ai_decision_event()]
        before = copy.deepcopy(events)

        report = build_case_event_builder_shape_report(events)
        report["keys_by_event_type"]["AI_DECISION_CREATED"].append("changed")

        self.assertEqual(events, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(case_event_builder_report).lower()

        forbidden_terms = [
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "from app.market_intelligence.case_event_builder",
            "import app.market_intelligence.case_event_builder",
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
