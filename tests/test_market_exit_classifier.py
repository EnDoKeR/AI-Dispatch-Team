import unittest

from app.market_intelligence.market_exit_classifier import classify_load_exit_market


class FakeLoad:
    def __init__(
        self,
        delivery="Denver, CO",
        rate=3600,
        total_rpm=2.8,
        driver_match_status="MATCH",
    ):
        self.delivery = delivery
        self.rate = rate
        self.total_rpm = total_rpm
        self.driver_match_status = driver_match_status


def baseline(median_rpm=2.25, median_rate=2800):
    return {
        "median_rpm": median_rpm,
        "median_rate": median_rate,
    }


def zone(
    city="Denver",
    state="CO",
    status="WEAK_EXIT_MARKET",
    clean=0,
    review=0,
    rate_check=0,
):
    return {
        "city": city,
        "state": state,
        "status": status,
        "clean_exit_count": clean,
        "review_exit_count": review,
        "rate_check_exit_count": rate_check,
    }


def zone_snapshot(cities=None, states=None):
    return {
        "cities": cities or {},
        "states": states or {},
    }


class TestMarketExitClassifier(unittest.TestCase):
    def test_strong_pay_risky_exit_recommends_reload_watch(self):
        result = classify_load_exit_market(
            FakeLoad(rate=3800, total_rpm=2.9),
            baseline=baseline(median_rpm=2.3, median_rate=3000),
            zone_snapshot=zone_snapshot(
                cities={
                    "Denver, CO": zone(
                        status="RISKY_EXIT_MARKET",
                        clean=0,
                        review=3,
                    )
                }
            ),
        )

        self.assertEqual(
            result["exit_status"],
            "STRONG_PAY_RELOAD_WATCH_RECOMMENDED",
        )
        self.assertTrue(result["recommend_reload_watch"])
        self.assertEqual(result["city_status"], "RISKY_EXIT_MARKET")

    def test_strong_pay_low_data_is_low_confidence_not_bad_market(self):
        result = classify_load_exit_market(
            FakeLoad(rate=3600, total_rpm=2.8),
            baseline=baseline(median_rpm=2.2, median_rate=2800),
            zone_snapshot=zone_snapshot(
                cities={
                    "Denver, CO": zone(
                        status="LOW_EXIT_CONFIDENCE",
                        clean=0,
                        review=1,
                    )
                }
            ),
        )

        self.assertEqual(result["exit_status"], "LOW_EXIT_CONFIDENCE")
        self.assertTrue(result["recommend_reload_watch"])
        self.assertIn("limited data", result["reason"].lower())

    def test_clean_exits_available(self):
        result = classify_load_exit_market(
            FakeLoad(rate=2600, total_rpm=2.4),
            baseline=baseline(),
            zone_snapshot=zone_snapshot(
                cities={
                    "Denver, CO": zone(
                        status="STRONG_EXIT_MARKET",
                        clean=2,
                        review=1,
                    )
                }
            ),
        )

        self.assertEqual(result["exit_status"], "CLEAN_EXIT_AVAILABLE")
        self.assertFalse(result["recommend_reload_watch"])
        self.assertEqual(result["clean_exit_count"], 2)

    def test_rate_check_exits_available_without_clean_exits(self):
        result = classify_load_exit_market(
            FakeLoad(rate=2600, total_rpm=2.3),
            baseline=baseline(),
            zone_snapshot=zone_snapshot(
                cities={
                    "Denver, CO": zone(
                        status="RISKY_EXIT_MARKET",
                        clean=0,
                        review=0,
                        rate_check=3,
                    )
                }
            ),
        )

        self.assertEqual(result["exit_status"], "RATE_CHECK_EXITS_AVAILABLE")
        self.assertEqual(result["rate_check_exit_count"], 3)

    def test_weak_load_weak_exit_does_not_falsely_mark_as_strong(self):
        result = classify_load_exit_market(
            FakeLoad(rate=1800, total_rpm=1.7),
            baseline=baseline(median_rpm=2.3, median_rate=2800),
            zone_snapshot=zone_snapshot(
                cities={
                    "Denver, CO": zone(
                        status="WEAK_EXIT_MARKET",
                        clean=0,
                        review=1,
                    )
                }
            ),
        )

        self.assertEqual(result["exit_status"], "WEAK_EXIT_MARKET")
        self.assertFalse(result["recommend_reload_watch"])

    def test_classifier_does_not_mutate_load(self):
        load = FakeLoad(rate=3600, total_rpm=2.8)
        before = dict(load.__dict__)

        classify_load_exit_market(
            load,
            baseline=baseline(),
            zone_snapshot=zone_snapshot(
                cities={
                    "Denver, CO": zone(status="LOW_EXIT_CONFIDENCE")
                }
            ),
        )

        self.assertEqual(load.__dict__, before)

    def test_missing_city_and_state_snapshot_returns_no_exit_context(self):
        result = classify_load_exit_market(
            FakeLoad(delivery="Denver, CO"),
            baseline=baseline(),
            zone_snapshot=zone_snapshot(),
        )

        self.assertEqual(result["exit_status"], "NO_EXIT_CONTEXT")
        self.assertFalse(result["recommend_reload_watch"])
        self.assertEqual(result["delivery_city"], "Denver")
        self.assertEqual(result["delivery_state"], "CO")

    def test_state_fallback_works_when_city_snapshot_is_missing(self):
        result = classify_load_exit_market(
            FakeLoad(delivery="Denver, CO"),
            baseline=baseline(),
            zone_snapshot=zone_snapshot(
                states={
                    "CO": zone(
                        city="",
                        state="CO",
                        status="STRONG_EXIT_MARKET",
                        clean=3,
                    )
                }
            ),
        )

        self.assertEqual(result["exit_status"], "CLEAN_EXIT_AVAILABLE")
        self.assertEqual(result["city_status"], "")
        self.assertEqual(result["state_status"], "STRONG_EXIT_MARKET")
        self.assertEqual(result["clean_exit_count"], 3)


if __name__ == "__main__":
    unittest.main()
