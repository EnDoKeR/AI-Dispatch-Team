import unittest

from app.market_intelligence.market_zone_snapshot import (
    build_market_zone_snapshot,
    city_state_key,
)


class FakeLoad:
    def __init__(
        self,
        pickup="Dallas, TX",
        delivery="Denver, CO",
        pickup_date="2026-05-28",
        reference_id="",
        broker_mc="123456",
        rate=2400,
        total_rpm=2.4,
        driver_match_status="MATCH",
        review_category="",
    ):
        self.pickup = pickup
        self.delivery = delivery
        self.pickup_date = pickup_date
        self.reference_id = reference_id
        self.broker_mc = broker_mc
        self.rate = rate
        self.total_rpm = total_rpm
        self.driver_match_status = driver_match_status
        self._review_category = review_category

    def review_category(self):
        return self._review_category


class TestMarketZoneSnapshot(unittest.TestCase):
    def test_city_state_key_normalizes_delivery_city_state(self):
        self.assertEqual(city_state_key("Denver, CO 80216"), "Denver, CO")
        self.assertEqual(city_state_key("Denver, CO"), "Denver, CO")
        self.assertEqual(city_state_key("Denver"), "Denver")

    def test_groups_loads_by_delivery_city_state(self):
        snapshot = build_market_zone_snapshot(
            [
                FakeLoad(reference_id="DEN-1", delivery="Denver, CO"),
                FakeLoad(reference_id="DEN-2", delivery="Denver, CO"),
                FakeLoad(reference_id="DAL-1", delivery="Dallas, TX"),
            ]
        )

        self.assertEqual(snapshot["cities"]["Denver, CO"]["city"], "Denver")
        self.assertEqual(snapshot["cities"]["Denver, CO"]["state"], "CO")
        self.assertEqual(snapshot["cities"]["Denver, CO"]["load_count"], 2)
        self.assertEqual(snapshot["cities"]["Dallas, TX"]["load_count"], 1)

    def test_state_summary_combines_cities(self):
        snapshot = build_market_zone_snapshot(
            [
                FakeLoad(reference_id="DEN-1", delivery="Denver, CO"),
                FakeLoad(reference_id="AUR-1", delivery="Aurora, CO"),
                FakeLoad(reference_id="DAL-1", delivery="Dallas, TX"),
            ]
        )

        self.assertEqual(snapshot["states"]["CO"]["state"], "CO")
        self.assertEqual(snapshot["states"]["CO"]["load_count"], 2)
        self.assertEqual(snapshot["states"]["TX"]["load_count"], 1)

    def test_duplicate_repost_loads_do_not_inflate_volume(self):
        snapshot = build_market_zone_snapshot(
            [
                FakeLoad(reference_id="", broker_mc="123456", rate=2400),
                FakeLoad(reference_id="", broker_mc="123456", rate=2600),
                FakeLoad(reference_id="", broker_mc="654321", rate=2500),
            ]
        )

        self.assertEqual(snapshot["source_load_count"], 3)
        self.assertEqual(snapshot["load_count"], 2)
        self.assertEqual(snapshot["cities"]["Denver, CO"]["load_count"], 2)

    def test_match_counts_as_clean_exit(self):
        snapshot = build_market_zone_snapshot(
            [
                FakeLoad(reference_id="MATCH-1", driver_match_status="MATCH"),
                FakeLoad(reference_id="MATCH-2", driver_match_status="MATCH"),
                FakeLoad(reference_id="MATCH-3", driver_match_status="MATCH"),
            ]
        )

        denver = snapshot["cities"]["Denver, CO"]

        self.assertEqual(denver["clean_exit_count"], 3)
        self.assertEqual(denver["review_exit_count"], 0)
        self.assertEqual(denver["blocked_count"], 0)

    def test_review_once_counts_as_review_exit(self):
        snapshot = build_market_zone_snapshot(
            [
                FakeLoad(
                    reference_id="REVIEW-1",
                    driver_match_status="REVIEW_ONCE",
                    review_category="CONESTOGA VERIFY",
                ),
                FakeLoad(
                    reference_id="REVIEW-2",
                    driver_match_status="REVIEW_ONCE",
                    review_category="DOCUMENTS",
                ),
                FakeLoad(reference_id="MATCH-1", driver_match_status="MATCH"),
            ]
        )

        denver = snapshot["cities"]["Denver, CO"]

        self.assertEqual(denver["review_exit_count"], 2)
        self.assertEqual(denver["rate_check_exit_count"], 0)

    def test_rate_check_counts_as_rate_check_exit_not_clean_exit(self):
        snapshot = build_market_zone_snapshot(
            [
                FakeLoad(
                    reference_id="RATE-1",
                    rate=0,
                    total_rpm=0,
                    driver_match_status="REVIEW_ONCE",
                    review_category="RATE CHECK",
                ),
                FakeLoad(
                    reference_id="RATE-2",
                    rate="",
                    total_rpm=0,
                    driver_match_status="REVIEW_ONCE",
                    review_category="RATE CHECK",
                ),
                FakeLoad(reference_id="MATCH-1", driver_match_status="MATCH"),
            ]
        )

        denver = snapshot["cities"]["Denver, CO"]

        self.assertEqual(denver["clean_exit_count"], 1)
        self.assertEqual(denver["review_exit_count"], 0)
        self.assertEqual(denver["rate_check_exit_count"], 2)

    def test_block_does_not_count_as_clean_exit(self):
        snapshot = build_market_zone_snapshot(
            [
                FakeLoad(reference_id="BLOCK-1", driver_match_status="BLOCK"),
                FakeLoad(reference_id="BLOCK-2", driver_match_status="BLOCK"),
                FakeLoad(reference_id="MATCH-1", driver_match_status="MATCH"),
            ]
        )

        denver = snapshot["cities"]["Denver, CO"]

        self.assertEqual(denver["clean_exit_count"], 1)
        self.assertEqual(denver["blocked_count"], 2)

    def test_low_data_classification_for_small_sample(self):
        snapshot = build_market_zone_snapshot(
            [
                FakeLoad(reference_id="ONE", total_rpm=3.0),
                FakeLoad(reference_id="TWO", total_rpm=3.2),
            ]
        )

        self.assertEqual(
            snapshot["cities"]["Denver, CO"]["status"],
            "LOW_EXIT_CONFIDENCE",
        )

    def test_strong_exit_market_with_enough_clean_exits_and_workable_median_rpm(self):
        snapshot = build_market_zone_snapshot(
            [
                FakeLoad(reference_id="A", total_rpm=2.2, driver_match_status="MATCH"),
                FakeLoad(reference_id="B", total_rpm=2.4, driver_match_status="MATCH"),
                FakeLoad(reference_id="C", total_rpm=2.6, driver_match_status="MATCH"),
            ]
        )

        denver = snapshot["cities"]["Denver, CO"]

        self.assertEqual(denver["median_rpm"], 2.4)
        self.assertEqual(denver["status"], "STRONG_EXIT_MARKET")

    def test_risky_exit_market_when_mostly_rate_check_or_review_and_no_clean_exits(self):
        snapshot = build_market_zone_snapshot(
            [
                FakeLoad(
                    reference_id="RATE-1",
                    rate=0,
                    total_rpm=0,
                    driver_match_status="REVIEW_ONCE",
                    review_category="RATE CHECK",
                ),
                FakeLoad(
                    reference_id="RATE-2",
                    rate=0,
                    total_rpm=0,
                    driver_match_status="REVIEW_ONCE",
                    review_category="RATE CHECK",
                ),
                FakeLoad(
                    reference_id="REVIEW-1",
                    total_rpm=2.1,
                    driver_match_status="REVIEW_ONCE",
                    review_category="CONESTOGA VERIFY",
                ),
            ]
        )

        denver = snapshot["cities"]["Denver, CO"]

        self.assertEqual(denver["clean_exit_count"], 0)
        self.assertEqual(denver["rate_check_exit_count"], 2)
        self.assertEqual(denver["review_exit_count"], 1)
        self.assertEqual(denver["status"], "RISKY_EXIT_MARKET")


if __name__ == "__main__":
    unittest.main()
