import unittest

from app.market_intelligence.broker_memory_core import (
    classify_broker_from_counts,
    format_broker_memory_status,
    is_valid_mc,
    normalize_mc,
)


class BrokerMemoryCoreTest(unittest.TestCase):
    def test_normalize_mc(self):
        self.assertEqual(normalize_mc(None), "")
        self.assertEqual(normalize_mc(" 123456 "), "123456")

    def test_is_valid_mc(self):
        self.assertTrue(is_valid_mc("123456"))
        self.assertFalse(is_valid_mc(""))
        self.assertFalse(is_valid_mc("NEEDS CHECK"))
        self.assertFalse(is_valid_mc("NO MC"))

    def test_bad_broker_feedback_creates_high_risk_review(self):
        result = classify_broker_from_counts(
            feedback_counts={"bad_broker": 2},
            case_counts={
                "total_cases": 3,
                "rate_check_cases": 1,
                "load_opportunity_cases": 1,
                "telegram_alerts": 1,
            },
        )

        self.assertEqual(result["status"], "BAD_BROKER_REVIEW")
        self.assertEqual(result["risk_level"], "HIGH")
        self.assertIn("bad_broker feedback 2x", result["reasons"])

    def test_rate_too_low_feedback_creates_rate_negotiation_required(self):
        result = classify_broker_from_counts(
            feedback_counts={"rate_too_low": 2},
            case_counts={
                "total_cases": 3,
                "rate_check_cases": 2,
                "load_opportunity_cases": 1,
                "telegram_alerts": 1,
            },
        )

        self.assertEqual(result["status"], "RATE_NEGOTIATION_REQUIRED")
        self.assertEqual(result["risk_level"], "MEDIUM")
        self.assertIn("rate_too_low feedback 2x", result["reasons"])

    def test_covered_feedback_creates_watchlist(self):
        result = classify_broker_from_counts(
            feedback_counts={"covered": 2},
            case_counts={
                "total_cases": 3,
                "rate_check_cases": 0,
                "load_opportunity_cases": 1,
                "telegram_alerts": 1,
            },
        )

        self.assertEqual(result["status"], "WATCHLIST")
        self.assertEqual(result["risk_level"], "MEDIUM")
        self.assertIn("covered feedback 2x", result["reasons"])

    def test_booked_feedback_creates_good_broker_status(self):
        result = classify_broker_from_counts(
            feedback_counts={"booked": 1},
            case_counts={
                "total_cases": 2,
                "rate_check_cases": 0,
                "load_opportunity_cases": 1,
                "telegram_alerts": 1,
            },
        )

        self.assertEqual(result["status"], "GOOD")
        self.assertEqual(result["risk_level"], "LOW")
        self.assertIn("booked feedback 1x", result["reasons"])

    def test_ratecon_received_feedback_creates_good_broker_status(self):
        result = classify_broker_from_counts(
            feedback_counts={"ratecon_received": 1},
            case_counts={
                "total_cases": 2,
                "rate_check_cases": 0,
                "load_opportunity_cases": 1,
                "telegram_alerts": 1,
            },
        )

        self.assertEqual(result["status"], "GOOD")
        self.assertEqual(result["risk_level"], "LOW")
        self.assertIn("ratecon_received feedback 1x", result["reasons"])

    def test_sent_to_driver_feedback_creates_good_broker_status(self):
        result = classify_broker_from_counts(
            feedback_counts={"sent_to_driver": 2},
            case_counts={
                "total_cases": 2,
                "rate_check_cases": 0,
                "load_opportunity_cases": 1,
                "telegram_alerts": 1,
            },
        )

        self.assertEqual(result["status"], "GOOD")
        self.assertEqual(result["risk_level"], "LOW")
        self.assertIn("sent_to_driver feedback 2x", result["reasons"])

    def test_called_broker_rate_check_creates_low_risk_watchlist(self):
        result = classify_broker_from_counts(
            feedback_counts={"called_broker": 2},
            case_counts={
                "total_cases": 2,
                "rate_check_cases": 1,
                "load_opportunity_cases": 1,
                "telegram_alerts": 1,
            },
        )

        self.assertEqual(result["status"], "WATCHLIST")
        self.assertEqual(result["risk_level"], "LOW")
        self.assertIn(
            "called_broker feedback 2x on rate-check activity",
            result["reasons"],
        )

    def test_cases_without_telegram_alerts_create_low_relevance(self):
        result = classify_broker_from_counts(
            feedback_counts={},
            case_counts={
                "total_cases": 3,
                "rate_check_cases": 0,
                "load_opportunity_cases": 1,
                "telegram_alerts": 0,
            },
        )

        self.assertEqual(result["status"], "LOW_RELEVANCE")
        self.assertEqual(result["risk_level"], "LOW")
        self.assertIn("3 cases but no Telegram alerts", result["reasons"])

    def test_many_rate_checks_without_opportunities_creates_rate_negotiation(self):
        result = classify_broker_from_counts(
            feedback_counts={},
            case_counts={
                "total_cases": 3,
                "rate_check_cases": 3,
                "load_opportunity_cases": 0,
                "telegram_alerts": 1,
            },
        )

        self.assertEqual(result["status"], "RATE_NEGOTIATION_REQUIRED")
        self.assertEqual(result["risk_level"], "MEDIUM")
        self.assertIn(
            "3 rate-check cases and no load opportunities",
            result["reasons"],
        )

    def test_unknown_when_no_signal(self):
        result = classify_broker_from_counts(
            feedback_counts={},
            case_counts={
                "total_cases": 1,
                "rate_check_cases": 0,
                "load_opportunity_cases": 1,
                "telegram_alerts": 1,
            },
        )

        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["risk_level"], "UNKNOWN")
        self.assertEqual(result["reasons"], [])

    def test_format_broker_memory_status_with_reasons(self):
        text = format_broker_memory_status(
            {
                "status": "BAD_BROKER_REVIEW",
                "risk_level": "HIGH",
                "reasons": ["bad_broker feedback 2x"],
            }
        )

        self.assertIn("BAD_BROKER_REVIEW / HIGH", text)
        self.assertIn("bad_broker feedback 2x", text)

    def test_format_broker_memory_status_without_reasons(self):
        text = format_broker_memory_status(
            {
                "status": "UNKNOWN",
                "risk_level": "UNKNOWN",
                "reasons": [],
            }
        )

        self.assertEqual(text, "UNKNOWN / UNKNOWN")


if __name__ == "__main__":
    unittest.main()
