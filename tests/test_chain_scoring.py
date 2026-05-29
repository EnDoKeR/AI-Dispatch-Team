import unittest

from app.market_intelligence.chain_scoring import score_two_load_chain


class FakeLoad:
    def __init__(
        self,
        pickup="Dallas, TX",
        delivery="Denver, CO",
        rate=3000,
        loaded_miles=1000,
        total_miles=1000,
        total_rpm=3.0,
        distances=None,
    ):
        self.pickup = pickup
        self.delivery = delivery
        self.rate = rate
        self.loaded_miles = loaded_miles
        self.total_miles = total_miles
        self.total_rpm = total_rpm
        self.distances = distances or {}

    def distance_between_known_cities(self, location_a, location_b):
        return self.distances.get((location_a, location_b))


def baseline(median_rpm=2.5):
    return {"median_rpm": median_rpm}


def zone_snapshot(status="STRONG_EXIT_MARKET"):
    return {
        "cities": {
            "Houston, TX": {
                "status": status,
                "clean_exit_count": 2,
                "review_exit_count": 0,
                "rate_check_exit_count": 0,
            }
        },
        "states": {},
    }


class TestChainScoring(unittest.TestCase):
    def test_strong_combined_rpm_vs_market_median(self):
        inbound = FakeLoad(
            delivery="Denver, CO",
            rate=3500,
            loaded_miles=1000,
            distances={("Denver, CO", "Boulder, CO"): 50},
        )
        exit_load = FakeLoad(
            pickup="Boulder, CO",
            delivery="Houston, TX",
            rate=3000,
            loaded_miles=900,
        )

        result = score_two_load_chain(
            inbound,
            exit_load,
            market_baseline=baseline(median_rpm=2.5),
            zone_snapshot=zone_snapshot(),
        )

        self.assertEqual(result["chain_status"], "STRONG_CHAIN")
        self.assertEqual(result["combined_gross"], 6500)
        self.assertEqual(result["empty_between_loads"], 50)
        self.assertTrue(result["empty_between_loads_known"])
        self.assertEqual(result["combined_miles"], 1950)
        self.assertEqual(result["combined_rpm"], 3.33)

    def test_workable_combined_rpm_vs_market_median(self):
        result = score_two_load_chain(
            FakeLoad(rate=2800, loaded_miles=1000),
            FakeLoad(
                pickup="Denver, CO",
                delivery="Houston, TX",
                rate=2800,
                loaded_miles=1000,
            ),
            market_baseline=baseline(median_rpm=2.55),
            zone_snapshot=zone_snapshot(),
        )

        self.assertEqual(result["chain_status"], "WORKABLE_CHAIN")
        self.assertEqual(result["combined_rpm"], 2.8)

    def test_weak_combined_rpm_vs_market_median(self):
        result = score_two_load_chain(
            FakeLoad(rate=2200, loaded_miles=1000),
            FakeLoad(
                pickup="Denver, CO",
                delivery="Houston, TX",
                rate=2200,
                loaded_miles=1000,
            ),
            market_baseline=baseline(median_rpm=2.6),
            zone_snapshot=zone_snapshot(),
        )

        self.assertEqual(result["chain_status"], "WEAK_CHAIN")
        self.assertEqual(result["combined_rpm"], 2.2)

    def test_rate_zero_exit_load_returns_rate_check_chain(self):
        result = score_two_load_chain(
            FakeLoad(rate=3000, loaded_miles=1000),
            FakeLoad(
                pickup="Denver, CO",
                delivery="Houston, TX",
                rate=0,
                loaded_miles=900,
            ),
            market_baseline=baseline(),
            zone_snapshot=zone_snapshot(),
        )

        self.assertEqual(result["chain_status"], "RATE_CHECK_CHAIN")
        self.assertIn("RATE_CHECK_CHAIN", result["context_labels"])

    def test_missing_rate_or_miles_returns_incomplete_chain_data(self):
        result = score_two_load_chain(
            FakeLoad(rate="", loaded_miles=1000),
            FakeLoad(
                pickup="Denver, CO",
                delivery="Houston, TX",
                rate=2500,
                loaded_miles=0,
            ),
            market_baseline=baseline(),
            zone_snapshot=zone_snapshot(),
        )

        self.assertEqual(result["chain_status"], "INCOMPLETE_CHAIN_DATA")

    def test_secondary_weak_exit_market_is_flagged(self):
        result = score_two_load_chain(
            FakeLoad(rate=3500, loaded_miles=1000),
            FakeLoad(
                pickup="Denver, CO",
                delivery="Houston, TX",
                rate=3000,
                loaded_miles=900,
            ),
            market_baseline=baseline(median_rpm=2.5),
            zone_snapshot=zone_snapshot(status="RISKY_EXIT_MARKET"),
        )

        self.assertEqual(result["secondary_exit_status"], "RISKY_EXIT_MARKET")
        self.assertIn("SECONDARY_EXIT_RISK", result["context_labels"])

    def test_helper_does_not_mutate_loads(self):
        inbound = FakeLoad(rate=3500, loaded_miles=1000)
        exit_load = FakeLoad(
            pickup="Denver, CO",
            delivery="Houston, TX",
            rate=3000,
            loaded_miles=900,
        )
        before_inbound = dict(inbound.__dict__)
        before_exit = dict(exit_load.__dict__)

        score_two_load_chain(
            inbound,
            exit_load,
            market_baseline=baseline(),
            zone_snapshot=zone_snapshot(),
        )

        self.assertEqual(inbound.__dict__, before_inbound)
        self.assertEqual(exit_load.__dict__, before_exit)

    def test_only_two_loads_are_evaluated(self):
        inbound = FakeLoad(rate=3000, loaded_miles=1000)
        exit_load = FakeLoad(
            pickup="Denver, CO",
            delivery="Houston, TX",
            rate=3000,
            loaded_miles=1000,
        )
        unused_third_load = FakeLoad(rate=9000, loaded_miles=100)

        result = score_two_load_chain(
            inbound,
            exit_load,
            market_baseline=baseline(median_rpm=2.5),
            zone_snapshot=zone_snapshot(),
        )

        self.assertEqual(unused_third_load.rate, 9000)
        self.assertEqual(result["leg_count"], 2)
        self.assertEqual(result["combined_gross"], 6000)


if __name__ == "__main__":
    unittest.main()
