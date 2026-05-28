import unittest

from app.market_intelligence.market_snapshot import (
    get_review_once_loads,
    get_top_opportunities,
)


class FakeLoad:
    def __init__(
        self,
        name,
        score,
        rate,
        total_rpm,
        empty_miles,
        good=True,
        driver_match_status="MATCH",
        driver_match_notes=None,
    ):
        self.name = name
        self._score = score
        self.rate = rate
        self.total_rpm = total_rpm
        self.empty_miles = empty_miles
        self._good = good
        self.driver_match_status = driver_match_status
        self.driver_match_notes = driver_match_notes or []

    def opportunity_score(self):
        return self._score

    def is_good(self):
        return self._good


class TestMarketSnapshotOpportunities(unittest.TestCase):
    def test_get_top_opportunities_returns_only_good_clean_matches(self):
        loads = [
            FakeLoad(
                name="best",
                score=95,
                rate=3000,
                total_rpm=2.8,
                empty_miles=20,
                good=True,
                driver_match_status="MATCH",
            ),
            FakeLoad(
                name="review",
                score=99,
                rate=5000,
                total_rpm=3.5,
                empty_miles=10,
                good=True,
                driver_match_status="REVIEW_ONCE",
            ),
            FakeLoad(
                name="blocked",
                score=100,
                rate=6000,
                total_rpm=4.0,
                empty_miles=5,
                good=True,
                driver_match_status="BLOCK",
            ),
            FakeLoad(
                name="not_good",
                score=98,
                rate=4500,
                total_rpm=3.2,
                empty_miles=15,
                good=False,
                driver_match_status="MATCH",
            ),
        ]

        top = get_top_opportunities(loads, limit=5)

        self.assertEqual([load.name for load in top], ["best"])

    def test_get_top_opportunities_sorts_by_score_rate_rpm_and_empty_miles(self):
        loads = [
            FakeLoad(
                name="lower_score",
                score=80,
                rate=5000,
                total_rpm=4.0,
                empty_miles=5,
            ),
            FakeLoad(
                name="higher_score",
                score=90,
                rate=2000,
                total_rpm=2.0,
                empty_miles=100,
            ),
            FakeLoad(
                name="same_score_higher_rate",
                score=90,
                rate=2500,
                total_rpm=2.0,
                empty_miles=100,
            ),
            FakeLoad(
                name="same_score_rate_higher_rpm",
                score=90,
                rate=2500,
                total_rpm=2.5,
                empty_miles=100,
            ),
            FakeLoad(
                name="same_score_rate_rpm_lower_empty",
                score=90,
                rate=2500,
                total_rpm=2.5,
                empty_miles=20,
            ),
        ]

        top = get_top_opportunities(loads, limit=5)

        self.assertEqual(
            [load.name for load in top],
            [
                "same_score_rate_rpm_lower_empty",
                "same_score_rate_higher_rpm",
                "same_score_higher_rate",
                "higher_score",
                "lower_score",
            ],
        )

    def test_get_top_opportunities_respects_limit(self):
        loads = [
            FakeLoad(name="one", score=90, rate=3000, total_rpm=3.0, empty_miles=10),
            FakeLoad(name="two", score=89, rate=2900, total_rpm=2.9, empty_miles=20),
            FakeLoad(name="three", score=88, rate=2800, total_rpm=2.8, empty_miles=30),
        ]

        top = get_top_opportunities(loads, limit=2)

        self.assertEqual([load.name for load in top], ["one", "two"])

    def test_get_review_once_loads_includes_good_review_once_loads(self):
        loads = [
            FakeLoad(
                name="good_review",
                score=80,
                rate=2000,
                total_rpm=2.0,
                empty_miles=10,
                good=True,
                driver_match_status="REVIEW_ONCE",
            ),
            FakeLoad(
                name="clean_match",
                score=95,
                rate=3000,
                total_rpm=3.0,
                empty_miles=5,
                good=True,
                driver_match_status="MATCH",
            ),
        ]

        review_once = get_review_once_loads(loads, limit=5)

        self.assertEqual([load.name for load in review_once], ["good_review"])

    def test_get_review_once_loads_includes_rate_check_even_when_not_good(self):
        loads = [
            FakeLoad(
                name="rate_check",
                score=40,
                rate=0,
                total_rpm=0,
                empty_miles=25,
                good=False,
                driver_match_status="REVIEW_ONCE",
                driver_match_notes=["Rate is missing from broker posting"],
            ),
            FakeLoad(
                name="not_good_not_rate_check",
                score=70,
                rate=1500,
                total_rpm=1.5,
                empty_miles=30,
                good=False,
                driver_match_status="REVIEW_ONCE",
                driver_match_notes=["Needs manual review"],
            ),
        ]

        review_once = get_review_once_loads(loads, limit=5)

        self.assertEqual([load.name for load in review_once], ["rate_check"])

    def test_get_review_once_loads_prioritizes_rate_check_reason(self):
        loads = [
            FakeLoad(
                name="good_review_high_score",
                score=95,
                rate=5000,
                total_rpm=4.0,
                empty_miles=5,
                good=True,
                driver_match_status="REVIEW_ONCE",
                driver_match_notes=["Conestoga verify"],
            ),
            FakeLoad(
                name="rate_check_lower_score",
                score=50,
                rate=0,
                total_rpm=0,
                empty_miles=50,
                good=False,
                driver_match_status="REVIEW_ONCE",
                driver_match_notes=["posted as $0"],
            ),
        ]

        review_once = get_review_once_loads(loads, limit=5)

        self.assertEqual(
            [load.name for load in review_once],
            ["rate_check_lower_score", "good_review_high_score"],
        )

    def test_get_review_once_loads_respects_limit(self):
        loads = [
            FakeLoad(
                name="one",
                score=90,
                rate=3000,
                total_rpm=3.0,
                empty_miles=10,
                good=True,
                driver_match_status="REVIEW_ONCE",
            ),
            FakeLoad(
                name="two",
                score=89,
                rate=2900,
                total_rpm=2.9,
                empty_miles=20,
                good=True,
                driver_match_status="REVIEW_ONCE",
            ),
            FakeLoad(
                name="three",
                score=88,
                rate=2800,
                total_rpm=2.8,
                empty_miles=30,
                good=True,
                driver_match_status="REVIEW_ONCE",
            ),
        ]

        review_once = get_review_once_loads(loads, limit=2)

        self.assertEqual([load.name for load in review_once], ["one", "two"])


if __name__ == "__main__":
    unittest.main()
