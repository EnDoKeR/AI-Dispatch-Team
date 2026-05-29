import copy
import inspect
import json
import unittest
from types import SimpleNamespace

from app.market_intelligence.decision_engine import result as decision_result
from app.market_intelligence.decision_engine.result import (
    build_decision_result,
    normalize_confidence,
    normalize_decision,
)


class DecisionEngineResultTest(unittest.TestCase):
    def test_builds_clean_match_result(self):
        result = build_decision_result(
            {
                "decision": "MATCH",
                "category": "LOAD OPPORTUNITY",
                "positive_signals": ["Strong gross"],
                "confidence": "HIGH",
                "source_signals": {"load_facts": {"rate": 3500}},
                "recommended_next_action": "CALL_NOW",
                "linked_load_id": "LOAD-1",
                "reference_id": "REF-1",
            }
        )

        self.assertEqual(result["decision"], "MATCH")
        self.assertEqual(result["category"], "LOAD OPPORTUNITY")
        self.assertEqual(result["positive_signals"], ["Strong gross"])
        self.assertEqual(result["confidence"], "HIGH")
        self.assertTrue(result["approval_required"])
        self.assertEqual(result["recommended_next_action"], "CALL_NOW")
        self.assertEqual(result["source_signals"]["load_facts"]["rate"], 3500)

    def test_builds_review_once_with_risk_flags_and_reasons(self):
        result = build_decision_result(
            decision="review once",
            category="RATE CHECK",
            risk_flags=["missing rate", "MISSING_RATE", "broker mc missing"],
            review_reasons="Rate needs broker check.",
            missing_fields=("rate",),
            needs_check_fields=["broker_mc"],
        )

        self.assertEqual(result["decision"], "REVIEW_ONCE")
        self.assertEqual(result["risk_flags"], ["MISSING_RATE", "BROKER_MC_MISSING"])
        self.assertEqual(result["review_reasons"], ["Rate needs broker check."])
        self.assertEqual(result["missing_fields"], ["rate"])
        self.assertEqual(result["needs_check_fields"], ["broker_mc"])
        self.assertTrue(result["approval_required"])

    def test_builds_block_with_block_reasons(self):
        result = build_decision_result(
            decision="BLOCK",
            category="BLOCK",
            risk_flags=["NO_CONESTOGA"],
            block_reasons=["Notes say Conestoga is not accepted."],
            approval_required=None,
        )

        self.assertEqual(result["decision"], "BLOCK")
        self.assertEqual(result["block_reasons"], ["Notes say Conestoga is not accepted."])
        self.assertFalse(result["approval_required"])

    def test_missing_fields_default_safely(self):
        result = build_decision_result()

        self.assertEqual(result["decision"], "NO_ACTION")
        self.assertEqual(result["category"], "")
        self.assertEqual(result["risk_flags"], [])
        self.assertEqual(result["missing_fields"], [])
        self.assertEqual(result["needs_check_fields"], [])
        self.assertEqual(result["review_reasons"], [])
        self.assertEqual(result["block_reasons"], [])
        self.assertEqual(result["positive_signals"], [])
        self.assertEqual(result["explanation"], "")
        self.assertEqual(result["confidence"], "UNKNOWN")
        self.assertEqual(result["source_signals"], {})
        self.assertFalse(result["approval_required"])

    def test_dedupes_risk_flags(self):
        result = build_decision_result(
            risk_flags=[
                "rate missing",
                "RATE_MISSING",
                "weak-exit-market",
                "WEAK_EXIT_MARKET",
            ]
        )

        self.assertEqual(result["risk_flags"], ["RATE_MISSING", "WEAK_EXIT_MARKET"])

    def test_json_serializable(self):
        result = build_decision_result(
            decision="MATCH",
            source_signals={"custom": SimpleNamespace(value="x")},
            positive_signals={1, 2},
        )

        json.dumps(result)
        self.assertEqual(result["source_signals"]["custom"], "namespace(value='x')")

    def test_does_not_mutate_input(self):
        source = {
            "decision": "REVIEW_ONCE",
            "risk_flags": ["MISSING_RATE"],
            "source_signals": {"load_facts": {"rate": 0}},
        }
        before = copy.deepcopy(source)

        result = build_decision_result(source)
        result["risk_flags"].append("NO_CONESTOGA")
        result["source_signals"]["load_facts"]["rate"] = 100

        self.assertEqual(source, before)

    def test_object_input_supported(self):
        source = SimpleNamespace(
            decision="MATCH",
            category="LOAD OPPORTUNITY",
            confidence="medium",
            risk_flags=["strong rpm"],
        )

        result = build_decision_result(source)

        self.assertEqual(result["decision"], "MATCH")
        self.assertEqual(result["category"], "LOAD OPPORTUNITY")
        self.assertEqual(result["confidence"], "MEDIUM")
        self.assertEqual(result["risk_flags"], ["STRONG_RPM"])

    def test_normalizers_fall_back_safely(self):
        self.assertEqual(normalize_decision("unknown"), "NO_ACTION")
        self.assertEqual(normalize_confidence("maybe"), "UNKNOWN")

    def test_no_forbidden_imports(self):
        source = inspect.getsource(decision_result).lower()

        forbidden_terms = [
            "telegram",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "pypdf",
            "gspread",
            "googlemaps",
            "dat_api",
            "apscheduler",
            "threading",
            "sqlite",
            "jsonl",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
