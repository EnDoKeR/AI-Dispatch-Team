import copy
import inspect
import json
import unittest

from app.market_intelligence import case_event_report
from app.market_intelligence.case_event_report import build_case_event_report


class CaseEventReportTest(unittest.TestCase):
    def test_empty_list_safe(self):
        report = build_case_event_report([])

        self.assertEqual(report["total_events"], 0)
        self.assertEqual(report["counts_by_event_type"], {})
        self.assertEqual(report["counts_by_event_group"], {})
        self.assertEqual(report["counts_by_case_id"], {})
        self.assertEqual(report["latest_event_by_case_id"], {})
        self.assertEqual(report["unknown_event_types"], [])
        self.assertEqual(report["timeline_by_case_id"], {})

    def test_counts_event_types(self):
        report = build_case_event_report([
            {"event_type": "AI_DECISION_CREATED", "case_id": "CASE-1"},
            {"event_type": "TELEGRAM_ALERT_SENT", "case_id": "CASE-1"},
            {"event_type": "TELEGRAM_ALERT_SENT", "case_id": "CASE-2"},
        ])

        self.assertEqual(report["counts_by_event_type"]["AI_DECISION_CREATED"], 1)
        self.assertEqual(report["counts_by_event_type"]["TELEGRAM_ALERT_SENT"], 2)

    def test_groups_event_types(self):
        report = build_case_event_report([
            {"event_type": "AI_DECISION_CREATED", "case_id": "CASE-1"},
            {"event_type": "MARKET_SNAPSHOT_SENT", "case_id": ""},
            {"event_type": "CLEAN_EXIT_FOUND", "case_id": "CASE-1"},
        ])

        self.assertEqual(report["counts_by_event_group"]["load_level"], 1)
        self.assertEqual(report["counts_by_event_group"]["search_reporting"], 1)
        self.assertEqual(report["counts_by_event_group"]["reload_watch"], 1)

    def test_groups_by_case_id(self):
        report = build_case_event_report([
            {"event_type": "AI_DECISION_CREATED", "case_id": "CASE-1"},
            {"event_type": "TELEGRAM_ALERT_SENT", "case_id": "CASE-1"},
            {"event_type": "RATECON_RECEIVED", "case_id": "CASE-2"},
        ])

        self.assertEqual(report["counts_by_case_id"]["CASE-1"], 2)
        self.assertEqual(report["counts_by_case_id"]["CASE-2"], 1)

    def test_identifies_unknown_event_types(self):
        report = build_case_event_report([
            {"event_type": "AI_DECISION_CREATED", "case_id": "CASE-1"},
            {"event_type": "UNPLANNED_EVENT", "case_id": "CASE-1"},
            {"event_type": "unplanned event", "case_id": "CASE-2"},
        ])

        self.assertEqual(report["unknown_event_types"], ["UNPLANNED_EVENT"])
        self.assertEqual(report["counts_by_event_group"]["unknown"], 2)

    def test_builds_timeline_and_latest_event_by_case_id(self):
        report = build_case_event_report([
            {
                "event_type": "AI_DECISION_CREATED",
                "case_id": "CASE-1",
                "timestamp_utc": "2026-05-29T10:00:00Z",
            },
            {
                "event_type": "TELEGRAM_ALERT_SENT",
                "case_id": "CASE-1",
                "timestamp_utc": "2026-05-29T10:05:00Z",
            },
        ])

        self.assertEqual(len(report["timeline_by_case_id"]["CASE-1"]), 2)
        self.assertEqual(
            report["latest_event_by_case_id"]["CASE-1"]["event_type"],
            "TELEGRAM_ALERT_SENT",
        )

    def test_missing_fields_are_tolerated(self):
        report = build_case_event_report([{}])

        self.assertEqual(report["total_events"], 1)
        self.assertEqual(report["counts_by_case_id"][""], 1)
        self.assertEqual(report["counts_by_event_group"]["unknown"], 1)
        self.assertEqual(report["timeline_by_case_id"][""][0]["event_type"], "")

    def test_report_is_json_serializable(self):
        report = build_case_event_report([
            {"event_type": "AI_DECISION_CREATED", "case_id": "CASE-1", "payload": {"x": object()}}
        ])

        json.dumps(report)

    def test_does_not_mutate_inputs(self):
        events = [
            {"event_type": "AI_DECISION_CREATED", "case_id": "CASE-1", "payload": {"x": 1}}
        ]
        before = copy.deepcopy(events)

        report = build_case_event_report(events)
        report["timeline_by_case_id"]["CASE-1"][0]["payload"]["x"] = 2

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
