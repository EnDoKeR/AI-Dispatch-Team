import copy
import inspect
import json
import unittest

from app.market_intelligence import case_event_built_report
from app.market_intelligence.case_event_built_report import (
    build_current_built_events_normalization_report,
)
from tests.fixtures.current_built_event_samples import CURRENT_BUILT_EVENT_SAMPLES


def fixture_events():
    return [
        copy.deepcopy(scenario["event"])
        for scenario in CURRENT_BUILT_EVENT_SAMPLES
    ]


class CaseEventBuiltReportTest(unittest.TestCase):
    def test_empty_report_safe(self):
        report = build_current_built_events_normalization_report([])

        self.assertEqual(report["total_events"], 0)
        self.assertEqual(report["known_event_count"], 0)
        self.assertEqual(report["unknown_event_count"], 0)
        self.assertEqual(report["warnings_count"], 0)
        self.assertEqual(report["warnings_by_type"], {})
        self.assertEqual(report["counts_by_event_type"], {})
        self.assertEqual(report["counts_by_event_group"], {})
        self.assertEqual(report["normalized_events"], [])

    def test_report_handles_all_fixtures(self):
        report = build_current_built_events_normalization_report(fixture_events())

        self.assertEqual(report["total_events"], len(CURRENT_BUILT_EVENT_SAMPLES))
        self.assertEqual(report["known_event_count"], 8)
        self.assertEqual(report["unknown_event_count"], 1)
        self.assertEqual(len(report["normalized_events"]), len(CURRENT_BUILT_EVENT_SAMPLES))

    def test_known_unknown_counts_correct(self):
        report = build_current_built_events_normalization_report(fixture_events())

        self.assertEqual(report["known_event_count"], 8)
        self.assertEqual(report["unknown_event_count"], 1)

    def test_warnings_summarized(self):
        report = build_current_built_events_normalization_report(fixture_events())

        self.assertEqual(report["warnings_count"], 4)
        self.assertEqual(report["warnings_by_type"]["missing_case_id"], 1)
        self.assertEqual(report["warnings_by_type"]["missing_timestamp_utc"], 1)
        self.assertEqual(report["warnings_by_type"]["missing_source"], 1)
        self.assertEqual(report["warnings_by_type"]["unknown_event_type"], 1)

    def test_event_type_counts_correct(self):
        report = build_current_built_events_normalization_report(fixture_events())

        self.assertEqual(report["counts_by_event_type"]["AI_DECISION_CREATED"], 1)
        self.assertEqual(report["counts_by_event_type"]["TELEGRAM_ALERT_SENT"], 2)
        self.assertEqual(report["counts_by_event_type"]["DISPATCHER_FEEDBACK_ADDED"], 2)
        self.assertEqual(report["counts_by_event_type"]["UNCLASSIFIED_CURRENT_EVENT"], 1)

    def test_event_group_counts_correct(self):
        report = build_current_built_events_normalization_report(fixture_events())

        self.assertEqual(report["counts_by_event_group"]["load_level"], 6)
        self.assertEqual(report["counts_by_event_group"]["load_board_simulation"], 2)
        self.assertEqual(report["counts_by_event_group"]["unknown"], 1)

    def test_report_is_json_serializable(self):
        report = build_current_built_events_normalization_report(fixture_events())

        json.dumps(report)

    def test_input_not_mutated(self):
        events = fixture_events()
        before = copy.deepcopy(events)

        report = build_current_built_events_normalization_report(events)
        report["normalized_events"][0]["legacy_payload"]["payload"] = {}

        self.assertEqual(events, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(case_event_built_report).lower()

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
