import copy
import inspect
import json
import unittest

from app.market_intelligence.decision_engine import timeline_preview_report
from app.market_intelligence.decision_engine.timeline_preview import (
    build_decision_result_timeline_preview,
)
from app.market_intelligence.decision_engine.timeline_preview_report import (
    build_decision_result_timeline_preview_report,
)


def preview(decision_result, case_id="CASE-1"):
    return build_decision_result_timeline_preview(
        decision_result,
        case_id=case_id,
        related_ids={"load_id": f"LOAD-{case_id}"},
    )


class DecisionEngineTimelinePreviewReportTest(unittest.TestCase):
    def test_empty_report_safe(self):
        report = build_decision_result_timeline_preview_report([])

        self.assertEqual(report["total_previews"], 0)
        self.assertEqual(report["counts_by_decision"], {})
        self.assertEqual(report["counts_by_risk_flag"], {})
        self.assertEqual(report["counts_by_case_id"], {})
        self.assertEqual(report["preview_payloads"], [])
        self.assertEqual(report["unknown_event_types"], [])
        self.assertEqual(report["validation_warnings"], [])

    def test_counts_decisions(self):
        report = build_decision_result_timeline_preview_report([
            preview({"decision": "MATCH"}, case_id="CASE-1"),
            preview({"decision": "REVIEW_ONCE"}, case_id="CASE-2"),
            preview({"decision": "REVIEW_ONCE"}, case_id="CASE-3"),
        ])

        self.assertEqual(report["counts_by_decision"]["MATCH"], 1)
        self.assertEqual(report["counts_by_decision"]["REVIEW_ONCE"], 2)

    def test_counts_risk_flags(self):
        report = build_decision_result_timeline_preview_report([
            preview({"decision": "REVIEW_ONCE", "risk_flags": ["RATE_MISSING"]}),
            preview(
                {
                    "decision": "REVIEW_ONCE",
                    "risk_flags": ["RATE_MISSING", "RATE_CHECK_REQUIRED"],
                }
            ),
        ])

        self.assertEqual(report["counts_by_risk_flag"]["RATE_MISSING"], 2)
        self.assertEqual(report["counts_by_risk_flag"]["RATE_CHECK_REQUIRED"], 1)

    def test_groups_by_case_id(self):
        report = build_decision_result_timeline_preview_report([
            preview({"decision": "MATCH"}, case_id="CASE-1"),
            preview({"decision": "BLOCK"}, case_id="CASE-1"),
            preview({"decision": "REVIEW_ONCE"}, case_id="CASE-2"),
        ])

        self.assertEqual(report["counts_by_case_id"]["CASE-1"], 2)
        self.assertEqual(report["counts_by_case_id"]["CASE-2"], 1)

    def test_all_preview_payloads_are_known_event_types(self):
        report = build_decision_result_timeline_preview_report([
            preview({"decision": "MATCH"}, case_id="CASE-1")
        ])

        self.assertEqual(report["unknown_event_types"], [])
        self.assertEqual(report["validation_warnings"], [])

    def test_unknown_event_types_and_warnings_are_reported(self):
        report = build_decision_result_timeline_preview_report([
            {
                "event_type": "FUTURE_DECISION",
                "case_id": "",
                "details": {
                    "preview_only": False,
                    "runtime_wired": True,
                },
            }
        ])

        self.assertEqual(report["unknown_event_types"], ["FUTURE_DECISION"])
        warnings = report["validation_warnings"][0]["warnings"]
        self.assertIn("unexpected_event_type", warnings)
        self.assertIn("unknown_event_type", warnings)
        self.assertIn("preview_only_not_true", warnings)
        self.assertIn("runtime_wired_not_false", warnings)
        self.assertIn("missing_decision_result", warnings)
        self.assertIn("missing_case_id", warnings)

    def test_report_is_json_serializable(self):
        report = build_decision_result_timeline_preview_report([
            preview({"decision": "MATCH", "source_signals": {"x": object()}})
        ])

        json.dumps(report)

    def test_does_not_mutate_inputs(self):
        previews = [
            preview(
                {
                    "decision": "REVIEW_ONCE",
                    "risk_flags": ["RATE_MISSING"],
                },
                case_id="CASE-1",
            )
        ]
        before = copy.deepcopy(previews)

        report = build_decision_result_timeline_preview_report(previews)
        report["preview_payloads"][0]["details"]["decision_result"]["risk_flags"].append(
            "CHANGED"
        )

        self.assertEqual(previews, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(timeline_preview_report).lower()

        forbidden_terms = [
            "telegram",
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
            "apply_search_request",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
