import copy
import inspect
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.market_intelligence.decision_engine import comparison_report
from app.market_intelligence.decision_engine.comparison_report import (
    build_decision_comparison,
    build_decision_comparison_report,
)


class ReviewLoad(SimpleNamespace):
    def review_category(self):
        return "RATE CHECK"


class DecisionEngineComparisonReportTest(unittest.TestCase):
    def test_clean_match_comparison_passes(self):
        load = SimpleNamespace(
            driver_match_status="MATCH",
            category="LOAD OPPORTUNITY",
            driver_match_notes=["Clean fit."],
            match_reasons=["Strong RPM."],
            reference_id="REF-1",
            load_id="LOAD-1",
        )

        comparison = build_decision_comparison(load)

        self.assertEqual(comparison["original_decision"], "MATCH")
        self.assertEqual(comparison["adapter_decision"], "MATCH")
        self.assertTrue(comparison["decision_matches"])
        self.assertTrue(comparison["category_matches"])
        self.assertEqual(comparison["reference_id"], "REF-1")
        self.assertEqual(comparison["load_id"], "LOAD-1")

    def test_review_once_comparison_passes(self):
        reason = "Rate is missing / posted as $0; dispatcher should check rate with broker."
        load = ReviewLoad(
            driver_match_status="REVIEW_ONCE",
            driver_match_notes=[reason],
            review_reasons=[reason],
            rate=0,
            reference_id="REF-2",
        )

        comparison = build_decision_comparison(load)

        self.assertEqual(comparison["original_decision"], "REVIEW_ONCE")
        self.assertEqual(comparison["original_category"], "RATE CHECK")
        self.assertEqual(comparison["adapter_decision"], "REVIEW_ONCE")
        self.assertEqual(comparison["adapter_category"], "RATE CHECK")
        self.assertTrue(comparison["decision_matches"])
        self.assertIn(reason, comparison["adapter_review_reasons"])
        self.assertIn("RATE_MISSING", comparison["adapter_risk_flags"])

    def test_block_comparison_passes(self):
        reason = "Notes say Conestoga is not accepted."
        load = SimpleNamespace(
            driver_match_status="BLOCK",
            driver_match_notes=[reason],
            block_reasons=[reason],
            is_blocked=True,
            reference_id="REF-3",
        )

        comparison = build_decision_comparison(load)

        self.assertEqual(comparison["original_decision"], "BLOCK")
        self.assertEqual(comparison["adapter_decision"], "BLOCK")
        self.assertTrue(comparison["decision_matches"])
        self.assertTrue(comparison["category_matches"])
        self.assertEqual(comparison["adapter_block_reasons"], [reason])
        self.assertIn("NO_CONESTOGA", comparison["adapter_risk_flags"])

    def test_missing_category_is_reported_safely(self):
        comparison = build_decision_comparison({})

        self.assertEqual(comparison["original_category"], "")
        self.assertEqual(comparison["adapter_category"], "")
        self.assertIn("missing_original_category", comparison["warnings"])
        self.assertIn("missing_original_decision", comparison["warnings"])
        self.assertIn("unknown_or_empty_decision", comparison["warnings"])

    def test_decision_mismatch_is_detected(self):
        load = SimpleNamespace(
            driver_match_status="MATCH",
            category="LOAD OPPORTUNITY",
        )

        with patch.object(
            comparison_report,
            "decision_result_from_market_load",
            return_value={
                "decision": "BLOCK",
                "category": "LOAD OPPORTUNITY",
                "review_reasons": [],
                "block_reasons": [],
                "risk_flags": [],
            },
        ):
            comparison = build_decision_comparison(load)

        self.assertEqual(comparison["original_decision"], "MATCH")
        self.assertEqual(comparison["adapter_decision"], "BLOCK")
        self.assertFalse(comparison["decision_matches"])
        self.assertTrue(comparison["category_matches"])

    def test_report_aggregates_counts(self):
        loads = [
            SimpleNamespace(driver_match_status="MATCH", category="LOAD OPPORTUNITY"),
            ReviewLoad(
                driver_match_status="REVIEW_ONCE",
                driver_match_notes=["Rate is missing / posted as $0."],
                review_reasons=["Rate is missing / posted as $0."],
                rate=0,
            ),
        ]

        report = build_decision_comparison_report(loads)

        self.assertEqual(report["total"], 2)
        self.assertEqual(report["decision_match_count"], 2)
        self.assertEqual(report["decision_mismatch_count"], 0)
        self.assertEqual(report["category_match_count"], 2)
        self.assertIn("RATE_MISSING", report["risk_flag_summary"])

    def test_report_is_json_serializable(self):
        report = build_decision_comparison_report([
            SimpleNamespace(driver_match_status="MATCH", category="LOAD OPPORTUNITY")
        ])

        json.dumps(report)

    def test_input_is_not_mutated(self):
        load = {
            "driver_match_status": "REVIEW_ONCE",
            "driver_match_notes": ["Rate is missing / posted as $0."],
            "review_reasons": ["Rate is missing / posted as $0."],
            "rate": 0,
        }
        before = copy.deepcopy(load)

        comparison = build_decision_comparison(load)
        comparison["original_reasons"].append("changed")

        self.assertEqual(load, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(comparison_report).lower()

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
