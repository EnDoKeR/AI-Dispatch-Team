import copy
import inspect
import json
import unittest
from types import SimpleNamespace

from app.market_intelligence.decision_engine import marketload_adapter
from app.market_intelligence.decision_engine.marketload_adapter import (
    decision_result_from_market_load,
)


class ReviewLoad(SimpleNamespace):
    def review_category(self):
        return "RATE CHECK"


class ExplodingLoad(SimpleNamespace):
    def apply_search_request(self, search_request):
        raise AssertionError("adapter must not recalculate decisions")


class DecisionEngineMarketLoadAdapterTest(unittest.TestCase):
    def test_match_like_load_maps_to_match_result(self):
        load = SimpleNamespace(
            driver_match_status="MATCH",
            driver_fit_status="CLEAN_MATCH",
            driver_match_notes=["Destination matches target city."],
            match_reasons=["Strong RPM."],
            review_reasons=[],
            block_reasons=[],
            is_clean_match=True,
            reference_id="REF-1",
            load_id="LOAD-1",
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["decision"], "MATCH")
        self.assertEqual(result["category"], "LOAD OPPORTUNITY")
        self.assertEqual(
            result["positive_signals"],
            ["Destination matches target city.", "Strong RPM."],
        )
        self.assertEqual(result["review_reasons"], [])
        self.assertEqual(result["block_reasons"], [])
        self.assertEqual(result["reference_id"], "REF-1")
        self.assertEqual(result["linked_load_id"], "LOAD-1")

    def test_review_once_like_load_maps_to_review_once_result(self):
        load = ReviewLoad(
            driver_match_status="REVIEW_ONCE",
            driver_fit_status="REVIEW_ONCE",
            driver_match_notes=[
                "Rate is missing / posted as $0; dispatcher should check rate with broker."
            ],
            match_reasons=[],
            review_reasons=[
                "Rate is missing / posted as $0; dispatcher should check rate with broker."
            ],
            block_reasons=[],
            rate=0,
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["decision"], "REVIEW_ONCE")
        self.assertEqual(result["category"], "RATE CHECK")
        self.assertEqual(
            result["review_reasons"],
            ["Rate is missing / posted as $0; dispatcher should check rate with broker."],
        )
        self.assertIn("RATE_MISSING", result["risk_flags"])
        self.assertIn("RATE_CHECK_REQUIRED", result["risk_flags"])
        self.assertEqual(result["missing_fields"], ["rate"])

    def test_block_like_load_maps_to_block_result(self):
        load = SimpleNamespace(
            driver_match_status="BLOCK",
            driver_fit_status="BLOCKED",
            driver_match_notes=["Notes say Conestoga is not accepted."],
            match_reasons=[],
            review_reasons=[],
            block_reasons=["Notes say Conestoga is not accepted."],
            is_blocked=True,
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["decision"], "BLOCK")
        self.assertEqual(result["category"], "BLOCK")
        self.assertEqual(
            result["block_reasons"],
            ["Notes say Conestoga is not accepted."],
        )
        self.assertEqual(result["risk_flags"], ["NO_CONESTOGA"])
        self.assertFalse(result["approval_required"])

    def test_missing_unknown_fields_produce_safe_defaults(self):
        result = decision_result_from_market_load({})

        self.assertEqual(result["decision"], "NO_ACTION")
        self.assertEqual(result["category"], "")
        self.assertEqual(result["risk_flags"], [])
        self.assertEqual(result["missing_fields"], [])
        self.assertEqual(result["needs_check_fields"], [])
        self.assertEqual(result["review_reasons"], [])
        self.assertEqual(result["block_reasons"], [])
        self.assertEqual(result["positive_signals"], [])
        self.assertEqual(result["reference_id"], "")
        self.assertEqual(result["linked_load_id"], "")

    def test_review_reasons_are_preserved_without_rewording(self):
        reason = "Posted as Flatbed/Step Deck; Conestoga must be verified."
        load = SimpleNamespace(
            driver_match_status="REVIEW_ONCE",
            driver_match_notes=[reason],
            review_reasons=[reason],
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["review_reasons"], [reason])
        self.assertIn("CONESTOGA_VERIFY", result["risk_flags"])

    def test_block_reasons_are_preserved_without_rewording(self):
        reason = "Tracking required, but driver profile says tracking is not accepted."
        load = SimpleNamespace(
            driver_match_status="BLOCK",
            driver_match_notes=[reason],
            block_reasons=[reason],
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["block_reasons"], [reason])
        self.assertIn("TRACKING_REQUIRED", result["risk_flags"])

    def test_reference_and_load_id_are_preserved(self):
        load = {
            "driver_match_status": "MATCH",
            "driver_match_notes": [],
            "reference_id": "REF-77",
            "id": "ROW-77",
        }

        result = decision_result_from_market_load(load)

        self.assertEqual(result["reference_id"], "REF-77")
        self.assertEqual(result["linked_load_id"], "ROW-77")

    def test_does_not_mutate_input_load(self):
        load = {
            "driver_match_status": "REVIEW_ONCE",
            "driver_match_notes": ["Rate check required."],
            "review_reasons": ["Rate check required."],
            "rate": 0,
        }
        before = copy.deepcopy(load)

        result = decision_result_from_market_load(load)
        result["review_reasons"].append("changed")

        self.assertEqual(load, before)

    def test_output_is_json_serializable(self):
        result = decision_result_from_market_load(
            SimpleNamespace(
                driver_match_status="MATCH",
                driver_match_notes=["Clean fit."],
                match_reasons=["Clean fit."],
            )
        )

        json.dumps(result)

    def test_adapter_does_not_call_apply_search_request(self):
        load = ExplodingLoad(
            driver_match_status="MATCH",
            driver_match_notes=["Clean fit."],
            match_reasons=["Clean fit."],
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["decision"], "MATCH")

    def test_no_forbidden_imports(self):
        source = inspect.getsource(marketload_adapter).lower()

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
