import copy
import inspect
import unittest

from app.market_intelligence import telegram_decision_result_formatter
from app.market_intelligence.telegram_decision_result_formatter import (
    format_decision_result_message,
)


REVIEW_RESULT = {
    "recommendation": "REVIEW_REQUIRED",
    "confidence": "LOW",
    "missing_fields": ["rate", "pickup_location"],
    "needs_check_fields": ["weight"],
    "low_confidence_fields": ["rate"],
    "risk_flags": ["LOW_CONFIDENCE_RATE"],
    "rules_fired": ["missing_critical_field_gate"],
    "reasons": ["Critical RateCon fields need dispatcher review."],
    "approval_required": True,
}


class TelegramDecisionResultFormatterTests(unittest.TestCase):
    def test_review_required_output_includes_missing_fields(self):
        message = format_decision_result_message(REVIEW_RESULT)

        self.assertIn("Recommendation: REVIEW_REQUIRED", message)
        self.assertIn("Missing critical fields:", message)
        self.assertIn("- rate", message)
        self.assertIn("- pickup_location", message)

    def test_low_confidence_fields_are_visible(self):
        message = format_decision_result_message(REVIEW_RESULT)

        self.assertIn("Low-confidence fields:", message)
        self.assertIn("- rate", message)
        self.assertIn("Risk flags:", message)
        self.assertIn("- LOW_CONFIDENCE_RATE", message)

    def test_missing_pickup_delivery_output_is_visible(self):
        result = dict(REVIEW_RESULT)
        result["missing_fields"] = ["pickup_location", "delivery_location"]

        message = format_decision_result_message(result)

        self.assertIn("- pickup_location", message)
        self.assertIn("- delivery_location", message)

    def test_next_human_action_is_shown_for_review_required(self):
        message = format_decision_result_message(REVIEW_RESULT)

        self.assertIn("Next human action:", message)
        self.assertIn("Review missing and low-confidence fields", message)

    def test_safe_output_uses_decision_result_recommendation(self):
        result = {
            "recommendation": "MATCH",
            "confidence": "HIGH",
            "missing_fields": [],
            "needs_check_fields": [],
            "risk_flags": [],
            "rules_fired": ["synthetic_rule"],
            "reasons": ["Synthetic result approved by upstream decision result."],
            "approval_required": False,
        }

        message = format_decision_result_message(result)

        self.assertIn("Recommendation: MATCH", message)
        self.assertNotIn("Next human action:", message)

    def test_missing_recommendation_falls_back_to_review_required(self):
        message = format_decision_result_message({"missing_fields": ["rate"]})

        self.assertIn("Recommendation: REVIEW_REQUIRED", message)
        self.assertIn("Next human action:", message)

    def test_formatter_does_not_mutate_decision_result(self):
        result = copy.deepcopy(REVIEW_RESULT)
        before = copy.deepcopy(result)

        format_decision_result_message(result)

        self.assertEqual(result, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(telegram_decision_result_formatter).lower()
        forbidden = [
            "decision_engine",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "pasted_text_parser",
            "pypdf",
            "pdfplumber",
            "gspread",
            "googlemaps",
            "dat_api",
            "openai",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
