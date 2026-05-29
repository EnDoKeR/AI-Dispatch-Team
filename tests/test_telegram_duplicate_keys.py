import unittest

from app.market_intelligence.telegram_duplicate_keys import (
    load_duplicate_key,
    load_duplicate_keys,
    load_repost_identity_key,
    load_update_signature,
    market_summary_key,
    normalize,
    remove_duplicates,
    search_health_key,
    sent_history_matches_load,
)


class FakeLoad:
    def __init__(
        self,
        pickup="Dallas, TX",
        delivery="Houston, TX",
        rate=2200,
        loaded_miles=240,
        broker="Test Broker",
        broker_name="",
        broker_mc="123456",
        pickup_date="2026-05-28",
        reference_id="",
        weight=36000,
        commodity="Steel",
        notes="Clean load",
        pickup_time="10 AM",
        delivery_time="2 PM",
    ):
        self.pickup = pickup
        self.delivery = delivery
        self.rate = rate
        self.loaded_miles = loaded_miles
        self.broker = broker
        self.broker_name = broker_name
        self.broker_mc = broker_mc
        self.pickup_date = pickup_date
        self.reference_id = reference_id
        self.weight = weight
        self.commodity = commodity
        self.notes = notes
        self.pickup_time = pickup_time
        self.delivery_time = delivery_time


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
            "alex|broker_mc_lane_date:123456|dallas, tx|houston, tx|2026-05-28",
        )

    def test_load_duplicate_key_prefers_valid_reference_id(self):
        load = FakeLoad(
            reference_id="REF-123",
            broker_mc="123456",
            rate=2200,
        )
        reposted_load = FakeLoad(
            reference_id="REF-123",
            broker_mc="999999",
            rate=2600,
        )

        self.assertEqual(
            load_duplicate_key(load, driver_name="Alex"),
            "alex|ref:ref-123",
        )
        self.assertEqual(
            load_duplicate_key(load, driver_name="Alex"),
            load_duplicate_key(reposted_load, driver_name="Alex"),
        )

    def test_load_duplicate_key_ignores_no_id_reference_and_uses_broker_mc_lane_date(self):
        load = FakeLoad(reference_id="NO ID", broker_mc="123456")

        self.assertEqual(
            load_duplicate_key(load, driver_name="Alex"),
            "alex|broker_mc_lane_date:123456|dallas, tx|houston, tx|2026-05-28",
        )

    def test_load_duplicate_key_uses_broker_name_when_broker_field_is_missing(self):
        load = FakeLoad(
            broker="",
            broker_name="Structured Broker",
            broker_mc="",
        )

        self.assertEqual(
            load_duplicate_key(load, driver_name="Alex"),
            "alex|broker_lane_date_rate_miles:structured broker|dallas, tx|houston, tx|2026-05-28|2200|240",
        )

    def test_load_duplicate_key_fallback_includes_weight_and_commodity(self):
        steel_load = FakeLoad(
            broker="",
            broker_name="",
            broker_mc="",
            weight=36000,
            commodity="Steel",
        )
        lumber_load = FakeLoad(
            broker="",
            broker_name="",
            broker_mc="",
            weight=42000,
            commodity="Lumber",
        )

        self.assertNotEqual(
            load_duplicate_key(steel_load, driver_name="Alex"),
            load_duplicate_key(lumber_load, driver_name="Alex"),
        )
        self.assertEqual(
            load_duplicate_key(steel_load, driver_name="Alex"),
            "alex|lane_date_rate_miles_weight_commodity:dallas, tx|houston, tx|2026-05-28|2200|240|36000|steel",
        )

    def test_repost_identity_and_update_signature_are_separate_concepts(self):
        original = FakeLoad(
            broker_mc="123456",
            rate=2200,
            notes="Clean load",
            pickup_time="10 AM",
        )
        updated = FakeLoad(
            broker_mc="123456",
            rate=2600,
            notes="Rate improved",
            pickup_time="11 AM",
        )

        self.assertEqual(
            load_repost_identity_key(original),
            load_repost_identity_key(updated),
        )
        self.assertEqual(
            load_duplicate_key(original, driver_name="Alex"),
            load_duplicate_key(updated, driver_name="Alex"),
        )
        self.assertNotEqual(
            load_update_signature(original),
            load_update_signature(updated),
        )

    def test_load_duplicate_keys_include_legacy_key_for_sent_history_compatibility(self):
        load = FakeLoad()

        self.assertEqual(
            load_duplicate_keys(load, driver_name="Alex"),
            [
                "alex|broker_mc_lane_date:123456|dallas, tx|houston, tx|2026-05-28",
                "alex|test broker|dallas, tx|houston, tx|2200|240|2026-05-28",
            ],
        )

    def test_sent_history_matches_current_or_legacy_key(self):
        load = FakeLoad()
        legacy_key = "alex|test broker|dallas, tx|houston, tx|2200|240|2026-05-28"

        self.assertTrue(
            sent_history_matches_load(
                {legacy_key},
                load,
                driver_name="Alex",
            )
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
            "alex|dallas, tx|10 am|flatbed|tx|dallas, tx|medium|700-1300|4|7|alex|broker_mc_lane_date:123456|dallas, tx|houston, tx|2026-05-28",
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
        unique = FakeLoad(rate=2500, broker_mc="654321")

        result = remove_duplicates(
            [first, duplicate, unique],
            search_request,
        )

        self.assertEqual(result, [first, unique])

    def test_remove_duplicates_treats_same_broker_lane_date_as_repost(self):
        search_request = FakeSearchRequest()
        first = FakeLoad(rate=2200, broker_mc="123456")
        reposted_with_new_rate = FakeLoad(rate=2500, broker_mc="123456")

        result = remove_duplicates(
            [first, reposted_with_new_rate],
            search_request,
        )

        self.assertEqual(result, [first])


if __name__ == "__main__":
    unittest.main()
