import copy
import unittest
from types import SimpleNamespace

from app.market_intelligence.decision_engine.marketload_adapter import (
    decision_result_from_market_load,
)


class ReviewCategoryLoad(SimpleNamespace):
    def review_category(self):
        return getattr(self, "_review_category", "GENERAL REVIEW")


class DecisionEngineMarketLoadAdapterRegressionTest(unittest.TestCase):
    def assert_load_unchanged(self, load, before):
        self.assertEqual(load.__dict__, before)

    def test_existing_clean_load_opportunity_fields_are_reflected(self):
        load = SimpleNamespace(
            driver_match_status="MATCH",
            driver_fit_status="CLEAN_MATCH",
            driver_match_notes=["Destination matches target city."],
            match_reasons=["Broker memory positive signal."],
            review_reasons=[],
            block_reasons=[],
            is_clean_match=True,
            reference_id="CLEAN-1",
            load_id="LOAD-CLEAN-1",
        )
        before = copy.deepcopy(load.__dict__)

        result = decision_result_from_market_load(load)

        self.assertEqual(result["decision"], "MATCH")
        self.assertEqual(result["category"], "LOAD OPPORTUNITY")
        self.assertEqual(
            result["positive_signals"],
            ["Destination matches target city.", "Broker memory positive signal."],
        )
        self.assertEqual(result["risk_flags"], [])
        self.assert_load_unchanged(load, before)

    def test_rate_check_review_once_fields_are_reflected(self):
        reason = "Rate is missing / posted as $0; dispatcher should check rate with broker."
        load = ReviewCategoryLoad(
            driver_match_status="REVIEW_ONCE",
            driver_fit_status="REVIEW_ONCE",
            driver_match_notes=[reason],
            review_reasons=[reason],
            block_reasons=[],
            match_reasons=[],
            rate=0,
            _review_category="RATE CHECK",
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["decision"], "REVIEW_ONCE")
        self.assertEqual(result["category"], "RATE CHECK")
        self.assertEqual(result["review_reasons"], [reason])
        self.assertIn("RATE_MISSING", result["risk_flags"])
        self.assertIn("RATE_CHECK_REQUIRED", result["risk_flags"])
        self.assertEqual(result["missing_fields"], ["rate"])

    def test_conestoga_verify_reason_maps_without_changing_decision(self):
        reason = "Posted as Flatbed/Step Deck; Conestoga must be verified."
        load = ReviewCategoryLoad(
            driver_match_status="REVIEW_ONCE",
            driver_fit_status="REVIEW_ONCE",
            driver_match_notes=[reason],
            review_reasons=[reason],
            block_reasons=[],
            match_reasons=[],
            _review_category="CONESTOGA VERIFY",
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["decision"], "REVIEW_ONCE")
        self.assertEqual(result["category"], "CONESTOGA VERIFY")
        self.assertEqual(result["review_reasons"], [reason])
        self.assertEqual(result["risk_flags"], ["CONESTOGA_VERIFY"])

    def test_broker_mc_missing_check_is_preserved_as_review_context(self):
        reason = "QuickPay payment language detected; check broker MC before buying."
        load = ReviewCategoryLoad(
            driver_match_status="REVIEW_ONCE",
            driver_fit_status="REVIEW_ONCE",
            driver_match_notes=[reason],
            review_reasons=[reason],
            block_reasons=[],
            match_reasons=[],
            broker_mc="",
            _review_category="BROKER REVIEW",
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["decision"], "REVIEW_ONCE")
        self.assertEqual(result["category"], "BROKER REVIEW")
        self.assertEqual(result["review_reasons"], [reason])
        self.assertIn("PAYMENT_RISK", result["risk_flags"])
        self.assertIn("BROKER_MC_MISSING", result["risk_flags"])
        self.assertEqual(result["missing_fields"], ["broker_mc"])

    def test_blocked_load_fields_are_reflected(self):
        reason = "Cash/Zelle type payment detected; likely no-buy / risky broker payment."
        load = SimpleNamespace(
            driver_match_status="BLOCK",
            driver_fit_status="BLOCKED",
            driver_match_notes=[reason],
            block_reasons=[reason],
            review_reasons=[],
            match_reasons=[],
            is_blocked=True,
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["decision"], "BLOCK")
        self.assertEqual(result["category"], "BLOCK")
        self.assertEqual(result["block_reasons"], [reason])
        self.assertIn("PAYMENT_RISK", result["risk_flags"])
        self.assertFalse(result["approval_required"])

    def test_missing_reference_id_stays_safe_default(self):
        load = SimpleNamespace(
            driver_match_status="MATCH",
            driver_fit_status="CLEAN_MATCH",
            driver_match_notes=["Clean fit."],
            match_reasons=["Clean fit."],
        )

        result = decision_result_from_market_load(load)

        self.assertEqual(result["decision"], "MATCH")
        self.assertEqual(result["reference_id"], "")
        self.assertNotIn("MISSING_REFERENCE_ID", result["risk_flags"])


if __name__ == "__main__":
    unittest.main()
