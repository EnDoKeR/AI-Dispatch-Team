import unittest

from app.market_intelligence.broker_memory_rules import (
    classify_broker_from_counts,
    get_broker_memory_status,
)
from app.market_intelligence.driver_lane_preference_rules import (
    classify_lane_signal,
)
from app.market_intelligence.driver_preference_rules import (
    classify_driver_from_counts,
)


class BrokerMemoryRulesTest(unittest.TestCase):
    def test_bad_broker_feedback_creates_high_risk_review(self):
        result = classify_broker_from_counts(
            feedback_counts={
                "bad_broker": 2,
            },
            case_counts={
                "total_cases": 3,
                "rate_check_cases": 1,
                "load_opportunity_cases": 1,
                "telegram_alerts": 2,
            },
        )

        self.assertEqual(result["status"], "BAD_BROKER_REVIEW")
        self.assertEqual(result["risk_level"], "HIGH")
        self.assertIn("bad_broker feedback 2x", result["reasons"])

    def test_rate_too_low_feedback_creates_rate_negotiation_required(self):
        result = classify_broker_from_counts(
            feedback_counts={
                "rate_too_low": 2,
            },
            case_counts={
                "total_cases": 3,
                "rate_check_cases": 2,
                "load_opportunity_cases": 0,
                "telegram_alerts": 2,
            },
        )

        self.assertEqual(result["status"], "RATE_NEGOTIATION_REQUIRED")
        self.assertEqual(result["risk_level"], "MEDIUM")
        self.assertIn("rate_too_low feedback 2x", result["reasons"])

    def test_booked_feedback_creates_good_broker_status(self):
        result = classify_broker_from_counts(
            feedback_counts={
                "booked": 1,
            },
            case_counts={
                "total_cases": 2,
                "rate_check_cases": 0,
                "load_opportunity_cases": 2,
                "telegram_alerts": 2,
            },
        )

        self.assertEqual(result["status"], "GOOD")
        self.assertEqual(result["risk_level"], "LOW")
        self.assertIn("booked feedback 1x", result["reasons"])

    def test_invalid_mc_returns_unknown_without_database_dependency(self):
        result = get_broker_memory_status("NEEDS CHECK")

        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["risk_level"], "UNKNOWN")
        self.assertIn("broker MC missing or not checked", result["reasons"])


class DriverPreferenceRulesTest(unittest.TestCase):
    def test_driver_strong_positive_with_small_sample_stays_informational(self):
        result = classify_driver_from_counts(
            feedback_counts={
                "booked": 1,
                "ratecon_received": 1,
            },
            case_counts={
                "feedback_items": 2,
                "telegram_alerts": 4,
                "load_opportunity_cases": 2,
                "rate_check_cases": 0,
            },
        )

        self.assertEqual(result["status"], "STRONG_POSITIVE")
        self.assertEqual(result["sample_quality"], "INSUFFICIENT_SAMPLE")
        self.assertEqual(result["sample_size"], 2)
        self.assertFalse(result["can_affect_decision"])

    def test_driver_reliable_sample_can_affect_decision_later(self):
        result = classify_driver_from_counts(
            feedback_counts={
                "sent_to_driver": 50,
            },
            case_counts={
                "feedback_items": 50,
                "telegram_alerts": 60,
                "load_opportunity_cases": 50,
                "rate_check_cases": 0,
            },
        )

        self.assertEqual(result["status"], "WEAK_POSITIVE")
        self.assertEqual(result["sample_quality"], "RELIABLE_PATTERN")
        self.assertEqual(result["sample_size"], 50)
        self.assertTrue(result["can_affect_decision"])

    def test_bad_broker_feedback_stays_broker_side_not_driver_preference(self):
        result = classify_driver_from_counts(
            feedback_counts={
                "bad_broker": 1,
            },
            case_counts={
                "feedback_items": 1,
                "telegram_alerts": 2,
                "load_opportunity_cases": 1,
                "rate_check_cases": 1,
            },
        )

        self.assertEqual(result["status"], "INSUFFICIENT_DRIVER_DATA")
        self.assertEqual(result["sample_quality"], "INSUFFICIENT_SAMPLE")
        self.assertFalse(result["can_affect_decision"])
        self.assertIn("bad_broker feedback 1x, should stay broker-side", result["reasons"])


class DriverLanePreferenceRulesTest(unittest.TestCase):
    def test_positive_lane_with_rate_sensitivity_small_sample_is_informational(self):
        result = classify_lane_signal(
            {
                "booked": 2,
                "sent_to_driver": 2,
                "rate_too_low": 1,
            }
        )

        self.assertEqual(result["status"], "POSITIVE_LANE_WITH_RATE_SENSITIVITY")
        self.assertEqual(result["sample_quality"], "INSUFFICIENT_SAMPLE")
        self.assertEqual(result["sample_size"], 5)
        self.assertFalse(result["can_affect_decision"])

    def test_broker_issue_is_not_driver_preference(self):
        result = classify_lane_signal(
            {
                "bad_broker": 2,
                "called_broker": 1,
            }
        )

        self.assertEqual(result["status"], "BROKER_ISSUE_NOT_DRIVER_PREFERENCE")
        self.assertEqual(result["sample_quality"], "INSUFFICIENT_SAMPLE")
        self.assertFalse(result["can_affect_decision"])

    def test_reliable_positive_lane_can_affect_decision_later(self):
        result = classify_lane_signal(
            {
                "booked": 25,
                "sent_to_driver": 25,
            }
        )

        self.assertEqual(result["status"], "POSITIVE_LANE")
        self.assertEqual(result["sample_quality"], "RELIABLE_PATTERN")
        self.assertEqual(result["sample_size"], 50)
        self.assertTrue(result["can_affect_decision"])

    def test_rate_sensitive_lane_with_small_sample_does_not_control_decision(self):
        result = classify_lane_signal(
            {
                "rate_too_low": 2,
            }
        )

        self.assertEqual(result["status"], "RATE_SENSITIVE_LANE")
        self.assertEqual(result["sample_quality"], "INSUFFICIENT_SAMPLE")
        self.assertFalse(result["can_affect_decision"])


if __name__ == "__main__":
    unittest.main()