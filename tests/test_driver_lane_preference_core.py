import unittest

from app.market_intelligence.driver_lane_preference_core import (
    average,
    classify_lane_signal,
    format_driver_lane_preference_status,
    format_lane_preference_status,
    get_sample_quality,
    is_valid_driver_name,
    lane_sample_size,
    normalize_location,
    normalize_text,
)


class DriverLanePreferenceCoreTest(unittest.TestCase):
    def test_normalize_text_and_location(self):
        self.assertEqual(normalize_text(None), "")
        self.assertEqual(normalize_text("  Alex  "), "Alex")
        self.assertEqual(normalize_location("  Dallas, TX  "), "dallas, tx")

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

    def test_lane_sample_size_and_average(self):
        self.assertEqual(
            lane_sample_size(
                {
                    "booked": 2,
                    "rate_too_low": 1,
                    "bad_broker": 0,
                }
            ),
            3,
        )
        self.assertEqual(average([]), 0)
        self.assertEqual(average([10, 20, 30]), 20)

    def test_classify_positive_lane_with_rate_sensitivity(self):
        result = classify_lane_signal(
            {
                "booked": 2,
                "sent_to_driver": 1,
                "rate_too_low": 1,
            }
        )

        self.assertEqual(result["status"], "POSITIVE_LANE_WITH_RATE_SENSITIVITY")
        self.assertEqual(result["confidence"], "MEDIUM")
        self.assertEqual(result["sample_size"], 4)
        self.assertFalse(result["can_affect_decision"])
        self.assertIn("positive feedback 3x", result["reasons"])
        self.assertIn("rate feedback 1x", result["reasons"])

    def test_classify_positive_lane_reliable_sample(self):
        result = classify_lane_signal(
            {
                "booked": 25,
                "sent_to_driver": 25,
            }
        )

        self.assertEqual(result["status"], "POSITIVE_LANE")
        self.assertEqual(result["confidence"], "HIGH")
        self.assertEqual(result["sample_size"], 50)
        self.assertEqual(result["sample_quality"], "RELIABLE_PATTERN")
        self.assertTrue(result["can_affect_decision"])

    def test_classify_broker_issue_not_driver_preference(self):
        result = classify_lane_signal(
            {
                "bad_broker": 2,
                "called_broker": 1,
            }
        )

        self.assertEqual(result["status"], "BROKER_ISSUE_NOT_DRIVER_PREFERENCE")
        self.assertEqual(result["confidence"], "MEDIUM")
        self.assertIn("broker/workflow feedback 3x", result["reasons"])

    def test_classify_rate_sensitive_lane(self):
        result = classify_lane_signal(
            {
                "rate_too_low": 2,
            }
        )

        self.assertEqual(result["status"], "RATE_SENSITIVE_LANE")
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn("rate feedback 2x", result["reasons"])

    def test_classify_market_timing_signal(self):
        result = classify_lane_signal(
            {
                "covered": 1,
            }
        )

        self.assertEqual(result["status"], "MARKET_TIMING_SIGNAL")
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn("market timing feedback 1x", result["reasons"])

    def test_classify_negative_or_unclear_feedback(self):
        result = classify_lane_signal(
            {
                "skipped": 1,
                "driver_rejected": 1,
            }
        )

        self.assertEqual(result["status"], "NEEDS_DRIVER_OR_DISPATCH_REVIEW")
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn("negative/unclear feedback 2x", result["reasons"])

    def test_format_lane_preference_status(self):
        text = format_lane_preference_status(
            {
                "status": "POSITIVE_LANE",
                "confidence": "HIGH",
                "sample_quality": "RELIABLE_PATTERN",
                "sample_size": 50,
                "reasons": ["positive feedback 50x"],
            }
        )

        self.assertIn("POSITIVE_LANE / HIGH / RELIABLE_PATTERN (50 signals)", text)
        self.assertIn("positive feedback 50x", text)

    def test_format_driver_lane_preference_status(self):
        text = format_driver_lane_preference_status(
            {
                "status": "RATE_SENSITIVE_LANE",
                "confidence": "LOW",
                "sample_quality": "INSUFFICIENT_SAMPLE",
                "sample_size": 2,
                "reasons": ["rate feedback 2x"],
            }
        )

        self.assertIn(
            "RATE_SENSITIVE_LANE / LOW / INSUFFICIENT_SAMPLE (2 signals)",
            text,
        )
        self.assertIn("rate feedback 2x", text)


if __name__ == "__main__":
    unittest.main()
