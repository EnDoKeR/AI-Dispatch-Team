import copy
import inspect
import json
import unittest

from app.market_intelligence.case_event_types import (
    EVENT_GROUP_LOAD_LEVEL,
    is_known_event_type,
)
from app.market_intelligence.decision_engine import timeline_preview
from app.market_intelligence.decision_engine.timeline_preview import (
    build_decision_result_timeline_preview,
)


class DecisionEngineTimelinePreviewTest(unittest.TestCase):
    def test_builds_ai_decision_created_preview_payload(self):
        preview = build_decision_result_timeline_preview(
            {"decision": "MATCH", "category": "LOAD OPPORTUNITY"},
            case_id="CASE-1",
            timestamp_utc="2026-05-29T10:00:00Z",
            related_ids={"load_id": "LOAD-1", "reference_id": "REF-1"},
        )

        self.assertEqual(preview["event_type"], "AI_DECISION_CREATED")
        self.assertEqual(preview["event_group"], EVENT_GROUP_LOAD_LEVEL)
        self.assertEqual(preview["case_id"], "CASE-1")
        self.assertEqual(preview["timestamp_utc"], "2026-05-29T10:00:00Z")
        self.assertEqual(preview["source"], "decision_engine_preview")
        self.assertEqual(preview["related_ids"]["load_id"], "LOAD-1")

    def test_embeds_decision_result(self):
        preview = build_decision_result_timeline_preview(
            {
                "decision": "REVIEW_ONCE",
                "category": "RATE CHECK",
                "risk_flags": ["RATE_MISSING"],
                "review_reasons": ["Rate is missing."],
            }
        )

        result = preview["details"]["decision_result"]

        self.assertEqual(result["decision"], "REVIEW_ONCE")
        self.assertEqual(result["category"], "RATE CHECK")
        self.assertEqual(result["risk_flags"], ["RATE_MISSING"])
        self.assertEqual(result["review_reasons"], ["Rate is missing."])

    def test_preview_only_true(self):
        preview = build_decision_result_timeline_preview({"decision": "MATCH"})

        self.assertTrue(preview["details"]["preview_only"])

    def test_runtime_wired_false(self):
        preview = build_decision_result_timeline_preview({"decision": "MATCH"})

        self.assertFalse(preview["details"]["runtime_wired"])

    def test_event_type_is_known_taxonomy_event(self):
        preview = build_decision_result_timeline_preview({"decision": "BLOCK"})

        self.assertTrue(is_known_event_type(preview["event_type"]))

    def test_payload_is_json_serializable(self):
        preview = build_decision_result_timeline_preview(
            {
                "decision": "MATCH",
                "source_signals": {"object": object()},
            }
        )

        json.dumps(preview)

    def test_does_not_mutate_inputs(self):
        decision_result = {
            "decision": "REVIEW_ONCE",
            "risk_flags": ["RATE_MISSING"],
            "source_signals": {"load": {"rate": 0}},
        }
        related_ids = {"load_id": "LOAD-1"}
        before_result = copy.deepcopy(decision_result)
        before_related_ids = copy.deepcopy(related_ids)

        preview = build_decision_result_timeline_preview(
            decision_result,
            related_ids=related_ids,
        )
        preview["details"]["decision_result"]["risk_flags"].append("CHANGED")
        preview["related_ids"]["load_id"] = "CHANGED"

        self.assertEqual(decision_result, before_result)
        self.assertEqual(related_ids, before_related_ids)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(timeline_preview).lower()

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
