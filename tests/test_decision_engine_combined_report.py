import copy
import inspect
import json
import unittest
from types import SimpleNamespace

from app.market_intelligence.decision_engine import combined_report
from app.market_intelligence.decision_engine.combined_report import (
    build_decision_timeline_comparison,
    build_decision_timeline_comparison_report,
)


def clean_match_load():
    return SimpleNamespace(
        case_id="CASE-COMBINED-1",
        load_id="LOAD-COMBINED-1",
        reference_id="REF-COMBINED-1",
        timestamp_utc="2026-05-29T10:00:00Z",
        driver_match_status="MATCH",
        category="LOAD OPPORTUNITY",
        driver_match_notes=["Synthetic clean lane fit."],
        match_reasons=["Synthetic strong RPM."],
    )


def review_once_load():
    reason = "Rate is missing / posted as $0; dispatcher should check rate with broker."

    return SimpleNamespace(
        case_id="CASE-COMBINED-2",
        load_id="LOAD-COMBINED-2",
        reference_id="REF-COMBINED-2",
        timestamp_utc="2026-05-29T10:05:00Z",
        driver_match_status="REVIEW_ONCE",
        category="RATE CHECK",
        driver_match_notes=[reason],
        review_reasons=[reason],
        rate=0,
    )


def block_load():
    reason = "Notes say Conestoga is not accepted."

    return SimpleNamespace(
        case_id="CASE-COMBINED-3",
        load_id="LOAD-COMBINED-3",
        reference_id="REF-COMBINED-3",
        timestamp_utc="2026-05-29T10:10:00Z",
        driver_match_status="BLOCK",
        category="BLOCK",
        driver_match_notes=[reason],
        block_reasons=[reason],
        is_blocked=True,
    )


class DecisionEngineCombinedReportTest(unittest.TestCase):
    def test_clean_match_report_item(self):
        item = build_decision_timeline_comparison(clean_match_load())

        self.assertEqual(item["original_decision"], "MATCH")
        self.assertEqual(item["decision_result"]["decision"], "MATCH")
        self.assertEqual(item["decision_result"]["category"], "LOAD OPPORTUNITY")
        self.assertEqual(item["load_id"], "LOAD-COMBINED-1")
        self.assertEqual(item["reference_id"], "REF-COMBINED-1")

    def test_review_once_report_item(self):
        item = build_decision_timeline_comparison(review_once_load())

        self.assertEqual(item["original_decision"], "REVIEW_ONCE")
        self.assertEqual(item["decision_result"]["decision"], "REVIEW_ONCE")
        self.assertEqual(item["decision_result"]["category"], "RATE CHECK")
        self.assertIn("RATE_MISSING", item["decision_result"]["risk_flags"])

    def test_block_report_item(self):
        item = build_decision_timeline_comparison(block_load())

        self.assertEqual(item["original_decision"], "BLOCK")
        self.assertEqual(item["decision_result"]["decision"], "BLOCK")
        self.assertEqual(item["decision_result"]["category"], "BLOCK")
        self.assertIn("NO_CONESTOGA", item["decision_result"]["risk_flags"])

    def test_timeline_preview_included(self):
        item = build_decision_timeline_comparison(clean_match_load())
        preview = item["timeline_preview_payload"]

        self.assertEqual(preview["event_type"], "AI_DECISION_CREATED")
        self.assertTrue(preview["details"]["preview_only"])
        self.assertFalse(preview["details"]["runtime_wired"])
        self.assertEqual(
            preview["details"]["decision_result"]["decision"],
            "MATCH",
        )

    def test_normalized_event_view_included(self):
        item = build_decision_timeline_comparison(clean_match_load())
        event_view = item["normalized_event_view"]

        self.assertIn("legacy_payload", event_view)
        self.assertIn("normalized_payload", event_view)
        self.assertEqual(
            event_view["normalized_payload"]["event_type"],
            "AI_DECISION_CREATED",
        )
        self.assertEqual(event_view["normalized_payload"]["event_group"], "load_level")

    def test_report_summary_counts_decisions(self):
        report = build_decision_timeline_comparison_report([
            clean_match_load(),
            review_once_load(),
            block_load(),
        ])

        self.assertTrue(report["dry_run"])
        self.assertEqual(report["total"], 3)
        self.assertEqual(report["decisions_by_type"]["MATCH"], 1)
        self.assertEqual(report["decisions_by_type"]["REVIEW_ONCE"], 1)
        self.assertEqual(report["decisions_by_type"]["BLOCK"], 1)
        self.assertEqual(report["preview_event_count"], 3)
        self.assertIn("RATE_MISSING", report["risk_flag_summary"])
        self.assertIn("NO_CONESTOGA", report["risk_flag_summary"])

    def test_report_is_json_serializable(self):
        report = build_decision_timeline_comparison_report([
            clean_match_load(),
            review_once_load(),
            block_load(),
        ])

        json.dumps(report)

    def test_input_is_not_mutated(self):
        load = {
            "case_id": "CASE-COMBINED-4",
            "load_id": "LOAD-COMBINED-4",
            "reference_id": "REF-COMBINED-4",
            "timestamp_utc": "2026-05-29T10:15:00Z",
            "driver_match_status": "REVIEW_ONCE",
            "category": "RATE CHECK",
            "driver_match_notes": ["Rate is missing / posted as $0."],
            "review_reasons": ["Rate is missing / posted as $0."],
            "rate": 0,
        }
        before = copy.deepcopy(load)

        item = build_decision_timeline_comparison(load)
        item["decision_result"]["risk_flags"].append("CHANGED")
        item["normalized_event_view"]["legacy_payload"] = {}

        self.assertEqual(load, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(combined_report).lower()

        forbidden_terms = [
            "telegram",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "repository",
            "pypdf",
            "gspread",
            "googlemaps",
            "dat_api",
            "apscheduler",
            "threading",
            "apply_search_request",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
