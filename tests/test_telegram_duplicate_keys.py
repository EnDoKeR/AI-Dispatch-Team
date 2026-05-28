import unittest

from app.market_intelligence.telegram_duplicate_keys import (
    load_duplicate_key,
    market_summary_key,
    normalize,
    remove_duplicates,
    search_health_key,
)


class FakeLoad:
    def __init__(
        self,
        pickup="Dallas, TX",
        delivery="Houston, TX",
        rate=2200,
        loaded_miles=240,
        broker="Test Broker",
        pickup_date="2026-05-28",
    ):
        self.pickup = pickup
        self.delivery = delivery
        self.rate = rate
        self.loaded_miles = loaded_miles
        self.broker = broker
        self.pickup_date = pickup_date


class FakeSearchRequest:
    driver_name = "Alex"
    current_location = "Dallas, TX"
    available_time = "10 AM"
    equipment = "Flatbed"
    target_direction = "TX"
    min_total_rpm = 2.0
    max_weight = 48000


class TestTelegramDuplicateKeys(unittest.TestCase):
    def test_normalize_strips_and_lowercases_values(self):
        self.assertEqual(normalize("  Dallas, TX  "), "dallas, tx")
        self.assertEqual(normalize(2200), "2200")
        self.assertEqual(normalize(None), "none")

    def test_load_duplicate_key_builds_stable_key(self):
        load = FakeLoad()

        key = load_duplicate_key(load, driver_name="Alex")

        self.assertEqual(
            key,
            "alex|test broker|dallas, tx|houston, tx|2200|240|2026-05-28",
        )

    def test_market_summary_key_uses_best_load_when_present(self):
        search_request = FakeSearchRequest()
        stats = {}
        recommendation = {
            "market_status": "MEDIUM",
            "best_bucket": "700-1300",
            "total_good_loads": 4,
            "total_qualified_loads": 7,
        }
        top_opportunities = [
            FakeLoad(
                pickup="Dallas, TX",
                delivery="Houston, TX",
                rate=2200,
                loaded_miles=240,
                broker="Best Broker",
                pickup_date="2026-05-28",
            )
        ]

        key = market_summary_key(
            stats=stats,
            recommendation=recommendation,
            top_opportunities=top_opportunities,
            search_location="Dallas, TX",
            search_request=search_request,
        )

        self.assertEqual(
            key,
            "alex|dallas, tx|10 am|flatbed|tx|dallas, tx|medium|700-1300|4|7|alex|best broker|dallas, tx|houston, tx|2200|240|2026-05-28",
        )

    def test_market_summary_key_uses_no_best_load_when_empty(self):
        search_request = FakeSearchRequest()
        recommendation = {
            "market_status": "BAD",
            "best_bucket": "0-450",
            "total_good_loads": 0,
            "total_qualified_loads": 1,
        }

        key = market_summary_key(
            stats={},
            recommendation=recommendation,
            top_opportunities=[],
            search_location="Dallas, TX",
            search_request=search_request,
        )

        self.assertTrue(key.endswith("|no_best_load"))

    def test_search_health_key_builds_stable_key(self):
        search_request = FakeSearchRequest()

        key = search_health_key(search_request)

        self.assertEqual(
            key,
            "alex|dallas, tx|10 am|flatbed|tx|2.0|48000",
        )

    def test_remove_duplicates_keeps_first_load_per_key(self):
        search_request = FakeSearchRequest()
        first = FakeLoad(rate=2200)
        duplicate = FakeLoad(rate=2200)
        unique = FakeLoad(rate=2500)

        result = remove_duplicates(
            [first, duplicate, unique],
            search_request,
        )

        self.assertEqual(result, [first, unique])


if __name__ == "__main__":
    unittest.main()
