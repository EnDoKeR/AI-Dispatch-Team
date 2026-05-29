import unittest

from app.market_intelligence.driver_preference_core import (
    classify_driver_from_counts,
    feedback_sample_size,
    format_driver_preference_status,
    get_sample_quality,
    is_valid_driver_name,
    normalize_driver_name,
)


class DriverPreferenceCoreTest(unittest.TestCase):
    def test_normalize_driver_name(self):
        self.assertEqual(normalize_driver_name(None), "")
        self.assertEqual(normalize_driver_name("  Alex  "), "Alex")

    def test_is_valid_driver_name(self):
        self.assertTrue(is_valid_driver_name("Alex"))
        self.assertFalse(is_valid_driver_name(""))
        self.assertFalse(is_valid_driver_name("UNKNOWN"))
        self.assertFalse(is_valid_driver_name("NEEDS CHECK"))
        self.assertFalse(is_valid_driver_name("NONE"))

    def test_get_sample_quality(self):
        self.assertEqual(
            get_sample_quality(0)["sample_quality"],
            "INSUFFICIENT_SAMPLE",
        )
        self.assertEqual(
            get_sample_quality(10)["sample_quality"],
            "EARLY_SIGNAL",
        )
        self.assertEqual(
            get_sample_quality(25)["sample_quality"],
            "DEVELOPING_PATTERN",
        )
        self.assertEqual(
            get_sample_quality(50)["sample_quality"],
            "RELIABLE_PATTERN",
        )
        self.assertFalse(get_sample_quality(25)["can_affect_decision"])
        self.assertTrue(get_sample_quality(50)["can_affect_decision"])

    def test_feedback_sample_size(self):
        self.assertEqual(feedback_sample_size({}), 0)
        self.assertEqual(
            feedback_sample_size(
                {
                    "booked": 2,
                    "ratecon_received": 1,
                    "skipped": 3,
                }
            ),
            6,
        )

    def test_classify_strong_positive_small_sample_is_informational(self):
        result = classify_driver_from_counts(
            feedback_counts={
                "booked": 1,
                "ratecon_received": 1,
            },
            case_counts={
                "feedback_items": 2,
                "telegram_alerts": 2,
            },
        )

        self.assertEqual(result["status"], "STRONG_POSITIVE")
        self.assertEqual(result["confidence"], "MEDIUM")
        self.assertEqual(result["sample_quality"], "INSUFFICIENT_SAMPLE")
        self.assertEqual(result["sample_size"], 2)
        self.assertFalse(result["can_affect_decision"])
        self.assertIn("booked feedback 1x", result["reasons"])
        self.assertIn("ratecon_received feedback 1x", result["reasons"])

    def test_classify_weak_positive_reliable_sample(self):
        result = classify_driver_from_counts(
            feedback_counts={
                "sent_to_driver": 50,
            },
            case_counts={
                "feedback_items": 50,
                "telegram_alerts": 60,
            },
        )

        self.assertEqual(result["status"], "WEAK_POSITIVE")
        self.assertEqual(result["confidence"], "MEDIUM")
        self.assertEqual(result["sample_quality"], "RELIABLE_PATTERN")
        self.assertEqual(result["sample_size"], 50)
        self.assertTrue(result["can_affect_decision"])

    def test_classify_driver_rejected_needs_review(self):
        result = classify_driver_from_counts(
            feedback_counts={
                "driver_rejected": 2,
            },
            case_counts={
                "feedback_items": 2,
            },
        )

        self.assertEqual(result["status"], "NEEDS_REVIEW")
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn("driver_rejected feedback 2x", result["reasons"])

    def test_classify_skipped_needs_review(self):
        result = classify_driver_from_counts(
            feedback_counts={
                "skipped": 2,
            },
            case_counts={
                "feedback_items": 2,
            },
        )

        self.assertEqual(result["status"], "NEEDS_REVIEW")
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn("skipped feedback 2x", result["reasons"])

    def test_classify_rate_sensitive(self):
        result = classify_driver_from_counts(
            feedback_counts={
                "rate_too_low": 2,
            },
            case_counts={
                "feedback_items": 2,
            },
        )

        self.assertEqual(result["status"], "RATE_SENSITIVE")
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn("rate_too_low feedback 2x", result["reasons"])

    def test_bad_broker_feedback_stays_broker_side(self):
        result = classify_driver_from_counts(
            feedback_counts={
                "bad_broker": 1,
            },
            case_counts={
                "feedback_items": 1,
                "telegram_alerts": 2,
            },
        )

        self.assertEqual(result["status"], "INSUFFICIENT_DRIVER_DATA")
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn(
            "bad_broker feedback 1x, should stay broker-side",
            result["reasons"],
        )

    def test_many_alerts_without_feedback_needs_more_feedback(self):
        result = classify_driver_from_counts(
            feedback_counts={},
            case_counts={
                "feedback_items": 0,
                "telegram_alerts": 5,
            },
        )

        self.assertEqual(result["status"], "NEEDS_MORE_FEEDBACK")
        self.assertIn("5 Telegram alerts but no feedback", result["reasons"])

    def test_many_load_opportunities_without_feedback_needs_more_feedback(self):
        result = classify_driver_from_counts(
            feedback_counts={},
            case_counts={
                "feedback_items": 0,
                "telegram_alerts": 0,
                "load_opportunity_cases": 3,
            },
        )

        self.assertEqual(result["status"], "NEEDS_MORE_FEEDBACK")
        self.assertIn("3 load opportunities but no feedback", result["reasons"])

    def test_many_rate_checks_without_feedback_needs_more_feedback(self):
        result = classify_driver_from_counts(
            feedback_counts={},
            case_counts={
                "feedback_items": 0,
                "telegram_alerts": 0,
                "load_opportunity_cases": 0,
                "rate_check_cases": 3,
            },
        )

        self.assertEqual(result["status"], "NEEDS_MORE_FEEDBACK")
        self.assertIn("3 rate-check cases but no feedback", result["reasons"])

    def test_format_driver_preference_status(self):
        text = format_driver_preference_status(
            {
                "status": "STRONG_POSITIVE",
                "confidence": "HIGH",
                "sample_quality": "RELIABLE_PATTERN",
                "sample_size": 50,
                "reasons": ["booked feedback 50x"],
            }
        )

        self.assertIn(
            "STRONG_POSITIVE / HIGH / RELIABLE_PATTERN (50 signals)",
            text,
        )
        self.assertIn("booked feedback 50x", text)


if __name__ == "__main__":
    unittest.main()
