import unittest

from app.market_intelligence.market_snapshot import (
    average_score,
    bucket_stats,
    choose_best_bucket,
    fit_stats,
    market_recommendation,
)


class FakeLoad:
    def __init__(
        self,
        bucket,
        score,
        total_rpm=2.0,
        rate=2000,
        qualified=True,
        good=True,
        driver_match_status="MATCH",
    ):
        self.bucket = bucket
        self._score = score
        self.total_rpm = total_rpm
        self.rate = rate
        self._qualified = qualified
        self._good = good
        self.driver_match_status = driver_match_status

    def opportunity_score(self):
        return self._score

    def is_qualified(self):
        return self._qualified

    def is_good(self):
        return self._good


class TestMarketSnapshotStats(unittest.TestCase):
    def test_average_score_returns_zero_for_empty_loads(self):
        self.assertEqual(average_score([]), 0)

    def test_average_score_rounds_average_opportunity_score(self):
        loads = [
            FakeLoad(bucket="0-450", score=80),
            FakeLoad(bucket="0-450", score=91),
        ]

        self.assertEqual(average_score(loads), 86)

    def test_bucket_stats_counts_loads_by_bucket_and_fit(self):
        loads = [
            FakeLoad(
                bucket="700-1300",
                score=90,
                total_rpm=2.5,
                rate=2500,
                qualified=True,
                good=True,
                driver_match_status="MATCH",
            ),
            FakeLoad(
                bucket="700-1300",
                score=75,
                total_rpm=2.0,
                rate=2000,
                qualified=True,
                good=True,
                driver_match_status="REVIEW_ONCE",
            ),
            FakeLoad(
                bucket="700-1300",
                score=40,
                total_rpm=1.5,
                rate=1500,
                qualified=False,
                good=False,
                driver_match_status="BLOCK",
            ),
            FakeLoad(
                bucket="1300+",
                score=85,
                total_rpm=2.2,
                rate=3300,
                qualified=True,
                good=True,
                driver_match_status="MATCH",
            ),
        ]

        stats = bucket_stats(loads)

        target_bucket = stats["700-1300"]

        self.assertEqual(target_bucket["total_loads"], 3)
        self.assertEqual(target_bucket["qualified_loads"], 2)
        self.assertEqual(target_bucket["good_loads"], 2)
        self.assertEqual(target_bucket["clean_match_loads"], 1)
        self.assertEqual(target_bucket["review_once_loads"], 1)
        self.assertEqual(target_bucket["blocked_loads"], 1)
        self.assertEqual(target_bucket["avg_total_rpm"], 2.0)
        self.assertEqual(target_bucket["avg_rate"], 2000)
        self.assertEqual(target_bucket["avg_opportunity_score"], 68)
        self.assertEqual(target_bucket["avg_qualified_score"], 82)
        self.assertEqual(target_bucket["avg_good_score"], 82)
        self.assertEqual(target_bucket["avg_clean_match_score"], 90)
        self.assertEqual(target_bucket["avg_review_once_score"], 75)

        empty_bucket = stats["0-450"]

        self.assertEqual(empty_bucket["total_loads"], 0)
        self.assertEqual(empty_bucket["avg_total_rpm"], 0)
        self.assertEqual(empty_bucket["avg_rate"], 0)
        self.assertEqual(empty_bucket["avg_opportunity_score"], 0)

    def test_fit_stats_marks_good_when_three_clean_matches_exist(self):
        loads = [
            FakeLoad(bucket="700-1300", score=90, driver_match_status="MATCH"),
            FakeLoad(bucket="700-1300", score=88, driver_match_status="MATCH"),
            FakeLoad(bucket="700-1300", score=86, driver_match_status="MATCH"),
            FakeLoad(
                bucket="700-1300",
                score=20,
                qualified=False,
                good=False,
                driver_match_status="BLOCK",
            ),
        ]

        fit = fit_stats(loads)

        self.assertEqual(fit["driver_fit"], "GOOD")
        self.assertEqual(fit["clean_matches"], 3)
        self.assertEqual(fit["review_once"], 0)
        self.assertEqual(fit["blocked"], 1)
        self.assertEqual(fit["qualified"], 3)
        self.assertEqual(fit["good"], 3)

    def test_fit_stats_marks_review_only_when_review_once_options_exist(self):
        loads = [
            FakeLoad(bucket="700-1300", score=80, driver_match_status="REVIEW_ONCE"),
            FakeLoad(bucket="700-1300", score=78, driver_match_status="REVIEW_ONCE"),
            FakeLoad(bucket="700-1300", score=76, driver_match_status="REVIEW_ONCE"),
        ]

        fit = fit_stats(loads)

        self.assertEqual(fit["driver_fit"], "REVIEW_ONLY")
        self.assertEqual(fit["clean_matches"], 0)
        self.assertEqual(fit["review_once"], 3)

    def test_choose_best_bucket_prefers_bucket_with_stronger_score(self):
        stats = {
            "0-450": {
                "clean_match_loads": 0,
                "good_loads": 1,
                "qualified_loads": 1,
                "avg_clean_match_score": 0,
                "avg_good_score": 70,
            },
            "700-1300": {
                "clean_match_loads": 2,
                "good_loads": 3,
                "qualified_loads": 3,
                "avg_clean_match_score": 90,
                "avg_good_score": 85,
            },
        }

        self.assertEqual(choose_best_bucket(stats), "700-1300")

    def test_market_recommendation_returns_expected_summary(self):
        stats = {
            "0-450": {
                "good_loads": 1,
                "qualified_loads": 1,
                "clean_match_loads": 0,
                "avg_clean_match_score": 0,
                "avg_good_score": 70,
            },
            "700-1300": {
                "good_loads": 3,
                "qualified_loads": 3,
                "clean_match_loads": 1,
                "avg_clean_match_score": 90,
                "avg_good_score": 85,
            },
        }
        fit = {
            "driver_fit": "WORKABLE",
            "clean_matches": 1,
            "review_once": 2,
            "blocked": 4,
        }

        recommendation = market_recommendation(stats, fit)

        self.assertEqual(recommendation["market_activity"], "MEDIUM")
        self.assertEqual(recommendation["market_status"], "MEDIUM")
        self.assertEqual(recommendation["driver_fit"], "WORKABLE")
        self.assertEqual(recommendation["action_status"], "SOME_MATCHES_AVAILABLE")
        self.assertEqual(recommendation["best_bucket"], "700-1300")
        self.assertEqual(recommendation["total_good_loads"], 4)
        self.assertEqual(recommendation["total_qualified_loads"], 4)
        self.assertEqual(recommendation["total_clean_matches"], 1)
        self.assertEqual(recommendation["total_review_once"], 2)
        self.assertEqual(recommendation["total_blocked"], 4)


if __name__ == "__main__":
    unittest.main()
