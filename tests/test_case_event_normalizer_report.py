import copy
import inspect
import json
import unittest

from app.market_intelligence import case_event_normalizer_report
from app.market_intelligence.case_event_normalizer_report import (
    build_case_event_normalizer_report,
)
from tests.fixtures.normalized_event_wrapper_cases import (
    NORMALIZED_EVENT_WRAPPER_CASES,
)


def fixture_events():
    return [
        copy.deepcopy(scenario["event"])
        for scenario in NORMALIZED_EVENT_WRAPPER_CASES
    ]


class CaseEventNormalizerReportTest(unittest.TestCase):
    def test_empty_report_safe(self):
        report = build_case_event_normalizer_report([])

        self.assertEqual(report["total_events"], 0)
        self.assertEqual(report["normalized_count"], 0)
        self.assertEqual(report["unknown_event_type_count"], 0)
        self.assertEqual(report["warnings_count"], 0)
        self.assertEqual(report["warnings_by_type"], {})
        self.assertEqual(report["counts_by_event_type"], {})
        self.assertEqual(report["counts_by_event_group"], {})
        self.assertEqual(report["normalized_events"], [])

    def test_report_counts_event_types(self):
        report = build_case_event_normalizer_report(fixture_events())

        self.assertEqual(report["counts_by_event_type"]["AI_DECISION_CREATED"], 1)
        self.assertEqual(report["counts_by_event_type"]["TELEGRAM_ALERT_SENT"], 2)
        self.assertEqual(report["counts_by_event_type"]["FUTURE_CUSTOM_EVENT"], 1)

    def test_report_counts_event_groups(self):
        report = build_case_event_normalizer_report(fixture_events())

        self.assertEqual(report["counts_by_event_group"]["load_level"], 5)
        self.assertEqual(report["counts_by_event_group"]["load_board_simulation"], 1)
        self.assertEqual(report["counts_by_event_group"]["search_reporting"], 1)
        self.assertEqual(report["counts_by_event_group"]["unknown"], 1)

    def test_report_counts_warnings(self):
        report = build_case_event_normalizer_report(fixture_events())

        self.assertEqual(report["warnings_count"], 3)
        self.assertEqual(report["warnings_by_type"]["missing_case_id"], 2)
        self.assertEqual(report["warnings_by_type"]["unknown_event_type"], 1)

    def test_unknown_event_counted(self):
        report = build_case_event_normalizer_report(fixture_events())

        self.assertEqual(report["unknown_event_type_count"], 1)

    def test_normalized_events_included(self):
        report = build_case_event_normalizer_report(fixture_events())

        self.assertEqual(report["normalized_count"], len(NORMALIZED_EVENT_WRAPPER_CASES))
        self.assertIn("legacy_payload", report["normalized_events"][0])
        self.assertIn("normalized_payload", report["normalized_events"][0])
        self.assertIn("warnings", report["normalized_events"][0])

    def test_report_is_json_serializable(self):
        report = build_case_event_normalizer_report([
            {
                "event_type": "AI_DECISION_CREATED",
                "case_id": "CASE-1",
                "timestamp_utc": "2026-05-29T10:00:00Z",
                "source": "synthetic_test",
                "payload": {"not_json": object()},
            }
        ])

        json.dumps(report)

    def test_does_not_mutate_inputs(self):
        events = fixture_events()
        before = copy.deepcopy(events)

        report = build_case_event_normalizer_report(events)
        report["normalized_events"][0]["legacy_payload"]["payload"] = {}

        self.assertEqual(events, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(case_event_normalizer_report).lower()

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
