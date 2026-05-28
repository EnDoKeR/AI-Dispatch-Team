import unittest

from app.market_intelligence.market_snapshot_explanation import build_market_explanation


class TestMarketSnapshotExplanation(unittest.TestCase):
    def test_build_market_explanation_returns_expected_lines(self):
        stats = {
            "700-1300": {
                "total_loads": 10,
                "qualified_loads": 6,
                "good_loads": 4,
                "clean_match_loads": 2,
                "review_once_loads": 1,
                "avg_total_rpm": 2.35,
                "avg_rate": 3100,
                "avg_clean_match_score": 88,
                "avg_review_once_score": 74,
            }
        }
        recommendation = {
            "market_activity": "MEDIUM",
            "driver_fit": "WORKABLE",
            "best_bucket": "700-1300",
        }

        explanation = build_market_explanation(stats, recommendation)

        self.assertEqual(
            explanation,
            [
                "Market activity is MEDIUM based on all current available loads.",
                "Driver fit is WORKABLE based on clean matches and review-once options.",
                "Best distance bucket is 700-1300 miles.",
                "This bucket has 10 total loads, 6 qualified loads, 4 good loads, 2 clean matches, and 1 review-once options.",
                "Average total RPM in this bucket is $2.35.",
                "Average gross in this bucket is $3100.",
                "Average score for clean matches is 88.",
                "Average score for review-once loads is 74.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
