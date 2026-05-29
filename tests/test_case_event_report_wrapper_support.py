import copy
import inspect
import json
import unittest

from app.market_intelligence import case_event_report
from app.market_intelligence.case_event_normalizer import normalize_case_event
from app.market_intelligence.case_event_report import build_case_event_report
from tests.fixtures.normalized_event_wrapper_cases import (
    NORMALIZED_EVENT_WRAPPER_CASES,
)


def legacy_event():
    return {
        "event_type": "AI_DECISION_CREATED",
        "case_id": "CASE-LEGACY-1",
        "timestamp_utc": "2026-05-29T10:00:00Z",
        "source": "synthetic_decision",
        "payload": {
            "decision": "MATCH",
        },
    }


def wrapper_event(scenario_id):
    for scenario in NORMALIZED_EVENT_WRAPPER_CASES:
        if scenario["scenario_id"] == scenario_id:
            return normalize_case_event(copy.deepcopy(scenario["event"]))

    raise AssertionError(f"Missing fixture scenario: {scenario_id}")


class CaseEventReportWrapperSupportTest(unittest.TestCase):
    def test_legacy_event_report_still_works(self):
        report = build_case_event_report([legacy_event()])

        self.assertEqual(report["total_events"], 1)
        self.assertEqual(report["counts_by_event_type"]["AI_DECISION_CREATED"], 1)
        self.assertEqual(report["counts_by_event_group"]["load_level"], 1)
        self.assertEqual(report["counts_by_case_id"]["CASE-LEGACY-1"], 1)
        self.assertEqual(report["warnings_count"], 0)
        self.assertEqual(report["warnings_by_type"], {})

    def test_wrapper_output_report_works(self):
        wrapper = wrapper_event("ai_decision_created_current_style")

        report = build_case_event_report([wrapper])
        timeline_event = report["timeline_by_case_id"]["CASE-AI-001"][0]

        self.assertEqual(report["total_events"], 1)
        self.assertEqual(report["counts_by_event_type"]["AI_DECISION_CREATED"], 1)
        self.assertEqual(report["counts_by_event_group"]["load_level"], 1)
        self.assertIn("legacy_payload", timeline_event)
        self.assertIn("details", timeline_event)
        self.assertIn("related_ids", timeline_event)

    def test_mixed_legacy_and_wrapper_report_works(self):
        wrapper = wrapper_event("telegram_alert_sent_current_style")

        report = build_case_event_report([legacy_event(), wrapper])

        self.assertEqual(report["total_events"], 2)
        self.assertEqual(report["counts_by_event_type"]["AI_DECISION_CREATED"], 1)
        self.assertEqual(report["counts_by_event_type"]["TELEGRAM_ALERT_SENT"], 1)
        self.assertEqual(report["counts_by_case_id"]["CASE-LEGACY-1"], 1)
        self.assertEqual(report["counts_by_case_id"]["CASE-TG-001"], 1)

    def test_wrapper_warnings_are_counted(self):
        wrappers = [
            wrapper_event("market_snapshot_sent_reporting_like"),
            wrapper_event("missing_case_id"),
            wrapper_event("unknown_event_type"),
        ]

        report = build_case_event_report(wrappers)

        self.assertEqual(report["warnings_count"], 3)
        self.assertEqual(report["warnings_by_type"]["missing_case_id"], 2)
        self.assertEqual(report["warnings_by_type"]["unknown_event_type"], 1)

    def test_normalized_event_group_is_used(self):
        wrapper = wrapper_event("ai_decision_created_current_style")
        wrapper["normalized_payload"]["event_group"] = "search_reporting"

        report = build_case_event_report([wrapper])

        self.assertEqual(report["counts_by_event_group"]["search_reporting"], 1)
        self.assertNotIn("load_level", report["counts_by_event_group"])

    def test_unknown_event_type_from_wrapper_is_reported(self):
        wrapper = wrapper_event("unknown_event_type")

        report = build_case_event_report([wrapper])

        self.assertEqual(report["unknown_event_types"], ["FUTURE_CUSTOM_EVENT"])
        self.assertEqual(report["counts_by_event_group"]["unknown"], 1)

    def test_report_is_json_serializable(self):
        report = build_case_event_report([
            legacy_event(),
            wrapper_event("ai_decision_created_current_style"),
        ])

        json.dumps(report)

    def test_does_not_mutate_inputs(self):
        events = [
            legacy_event(),
            wrapper_event("ai_decision_created_current_style"),
        ]
        before = copy.deepcopy(events)

        report = build_case_event_report(events)
        report["timeline_by_case_id"]["CASE-AI-001"][0]["legacy_payload"] = {}

        self.assertEqual(events, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(case_event_report).lower()

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
