import unittest

from app.market_intelligence.market_models import (
    MarketLoad,
    location_has_state,
    location_state,
    normalize_location_text,
)


class TestMarketModelHelpers(unittest.TestCase):
    def test_normalize_location_text_strips_and_lowercases(self):
        self.assertEqual(normalize_location_text("  Dallas, TX  "), "dallas, tx")
        self.assertEqual(normalize_location_text(None), "")
        self.assertEqual(normalize_location_text(123), "123")

    def test_location_has_state_matches_comma_and_space_formats(self):
        self.assertTrue(location_has_state("Dallas, TX", "TX"))
        self.assertTrue(location_has_state("Dallas TX", "TX"))
        self.assertTrue(location_has_state("Dallas, TX 75201", "TX"))

    def test_location_has_state_returns_false_for_missing_or_wrong_state(self):
        self.assertFalse(location_has_state("", "TX"))
        self.assertFalse(location_has_state("Dallas, TX", "FL"))
        self.assertFalse(location_has_state("Dallas", "TX"))
        self.assertFalse(location_has_state("Dallas, TX", ""))

    def test_location_state_extracts_two_letter_state(self):
        self.assertEqual(location_state("Dallas, TX"), "TX")
        self.assertEqual(location_state("Dallas TX"), "TX")
        self.assertEqual(location_state("Chicago, IL"), "IL")

    def test_location_state_returns_empty_when_state_is_missing_or_invalid(self):
        self.assertEqual(location_state("Dallas"), "")
        self.assertEqual(location_state("Dallas, Texas"), "")
        self.assertEqual(location_state(""), "")


class TestMarketLoadBasics(unittest.TestCase):
    def test_market_load_initializes_core_fields_and_calculated_values(self):
        load = MarketLoad(
            origin="Dallas, TX",
            destination="Houston, TX",
            rate="2200",
            loaded_miles="240",
            empty_miles="20",
            weight="36000",
            posted_trailer_type="Flatbed",
            equipment="Flatbed",
            pickup_time="10 AM",
            delivery_time="2 PM",
            broker_name="Test Broker",
            broker_mc="123456",
            broker_contact="dispatch@example.com",
            parsed_contact={
                "email": "dispatch@example.com",
                "phone": "555-111-2222",
            },
            reference_id="REF-123",
            is_bookable="true",
            is_tracking_required="yes",
            delivery_zone="GOOD / STRONG RELOAD AREA",
        )

        self.assertEqual(load.pickup, "Dallas, TX")
        self.assertEqual(load.delivery, "Houston, TX")
        self.assertEqual(load.origin, "Dallas, TX")
        self.assertEqual(load.destination, "Houston, TX")
        self.assertEqual(load.rate, 2200)
        self.assertEqual(load.loaded_miles, 240)
        self.assertEqual(load.empty_miles, 20)
        self.assertEqual(load.total_miles, 260)
        self.assertEqual(load.total_rpm, 8.46)
        self.assertEqual(load.weight, 36000)
        self.assertEqual(load.posted_trailer_type, "Flatbed")
        self.assertEqual(load.equipment, "Flatbed")
        self.assertEqual(load.pickup_time, "10 AM")
        self.assertEqual(load.delivery_time, "2 PM")
        self.assertEqual(load.broker_name, "Test Broker")
        self.assertEqual(load.broker_mc, "123456")
        self.assertEqual(load.primary_email, "dispatch@example.com")
        self.assertEqual(load.primary_phone, "555-111-2222")
        self.assertEqual(load.reference_id, "REF-123")
        self.assertTrue(load.is_bookable)
        self.assertTrue(load.is_tracking_required)
        self.assertEqual(load.delivery_zone, "GOOD / STRONG RELOAD AREA")
        self.assertEqual(load.bucket, "0-450")
        self.assertEqual(load.driver_match_status, "UNKNOWN")

    def test_market_load_uses_pickup_delivery_as_origin_destination_fallbacks(self):
        load = MarketLoad(
            pickup="Austin, TX",
            delivery="San Antonio, TX",
            rate=1000,
            loaded_miles=80,
            empty_miles=0,
        )

        self.assertEqual(load.origin, "Austin, TX")
        self.assertEqual(load.destination, "San Antonio, TX")
        self.assertEqual(load.pickup, "Austin, TX")
        self.assertEqual(load.delivery, "San Antonio, TX")
        self.assertEqual(load.total_miles, 80)
        self.assertEqual(load.total_rpm, 12.5)

    def test_market_load_uses_explicit_total_miles_when_provided(self):
        load = MarketLoad(
            pickup="Dallas, TX",
            delivery="Houston, TX",
            rate=1200,
            loaded_miles=200,
            empty_miles=50,
            total_miles=300,
        )

        self.assertEqual(load.total_miles, 300)
        self.assertEqual(load.total_rpm, 4.0)

    def test_market_load_loaded_rpm_and_keys(self):
        load = MarketLoad(
            origin="Dallas, TX",
            destination="Houston, TX",
            rate=1200,
            loaded_miles=300,
            broker_name="Test Broker",
            broker_mc="123456",
        )

        self.assertEqual(load.loaded_rpm(), 4.0)
        self.assertEqual(load.lane_key(), "Dallas, TX -> Houston, TX")
        self.assertEqual(load.broker_key(), "Test Broker|123456")

    def test_market_load_bucket_calculation(self):
        self.assertEqual(MarketLoad(rate=1000, loaded_miles=100).bucket, "0-450")
        self.assertEqual(MarketLoad(rate=1000, loaded_miles=500).bucket, "450-700")
        self.assertEqual(MarketLoad(rate=1000, loaded_miles=900).bucket, "700-1300")
        self.assertEqual(MarketLoad(rate=1000, loaded_miles=1400).bucket, "1300+")



class FakeSearchRequest:
    def __init__(
        self,
        target_direction="TX",
        target_city="",
        target_radius_miles=0,
    ):
        self.target_direction = target_direction
        self.target_city = target_city
        self.target_radius_miles = target_radius_miles


class TestMarketLoadTargetMatching(unittest.TestCase):
    def test_target_states_returns_known_direction_states(self):
        load = MarketLoad()

        self.assertEqual(load.target_states(FakeSearchRequest(target_direction="TX")), ["TX"])
        self.assertIn("IL", load.target_states(FakeSearchRequest(target_direction="midwest")))
        self.assertEqual(load.target_states(FakeSearchRequest(target_direction="unknown")), [])

    def test_route_toward_target_states_returns_route_states(self):
        load = MarketLoad()

        route_states = load.route_toward_target_states(
            FakeSearchRequest(target_direction="TX")
        )

        self.assertIn("AL", route_states)
        self.assertIn("TX", route_states)

    def test_delivery_matches_target_when_delivery_state_is_target(self):
        load = MarketLoad(
            pickup="Dallas, TX",
            delivery="Houston, TX",
            rate=2200,
            loaded_miles=240,
        )

        self.assertTrue(
            load.delivery_matches_target(FakeSearchRequest(target_direction="TX"))
        )

    def test_delivery_matches_target_returns_false_for_non_target_state(self):
        load = MarketLoad(
            pickup="Dallas, TX",
            delivery="Denver, CO",
            rate=2200,
            loaded_miles=800,
        )

        self.assertFalse(
            load.delivery_matches_target(FakeSearchRequest(target_direction="TX"))
        )

    def test_delivery_is_along_route_for_route_state(self):
        load = MarketLoad(
            pickup="Atlanta, GA",
            delivery="Birmingham, AL",
            rate=1200,
            loaded_miles=150,
        )

        self.assertTrue(
            load.delivery_is_along_route(FakeSearchRequest(target_direction="TX"))
        )

    def test_should_block_off_target_for_non_target_non_route_load(self):
        load = MarketLoad(
            pickup="Dallas, TX",
            delivery="Denver, CO",
            rate=1200,
            loaded_miles=800,
            empty_miles=50,
        )

        self.assertTrue(
            load.should_block_off_target(FakeSearchRequest(target_direction="TX"))
        )

    def test_should_not_block_strong_off_target_exception(self):
        load = MarketLoad(
            pickup="Dallas, TX",
            delivery="Denver, CO",
            rate=3000,
            loaded_miles=500,
            empty_miles=50,
        )

        self.assertTrue(load.is_strong_off_target_exception())
        self.assertFalse(
            load.should_block_off_target(FakeSearchRequest(target_direction="TX"))
        )

    def test_off_target_review_reason_for_along_route_load(self):
        load = MarketLoad(
            pickup="Atlanta, GA",
            delivery="Birmingham, AL",
            rate=1200,
            loaded_miles=150,
        )

        reason = load.off_target_review_reason(
            FakeSearchRequest(target_direction="TX")
        )

        self.assertEqual(reason, "Load is along route toward TX.")

    def test_off_target_review_reason_for_strong_exception(self):
        load = MarketLoad(
            pickup="Dallas, TX",
            delivery="Denver, CO",
            rate=3000,
            loaded_miles=500,
            empty_miles=50,
        )

        reason = load.off_target_review_reason(
            FakeSearchRequest(target_direction="TX")
        )

        self.assertIn("Strong off-target exception", reason)
        self.assertIn("RPM $", reason)
        self.assertIn("gross $3000", reason)

    def test_matches_target_state_or_region(self):
        target_load = MarketLoad(delivery="Houston, TX")
        midwest_load = MarketLoad(delivery="Chicago, IL")
        miss_load = MarketLoad(delivery="Denver, CO")

        self.assertTrue(
            target_load.matches_target_state_or_region(
                FakeSearchRequest(target_direction="TX")
            )
        )
        self.assertTrue(
            midwest_load.matches_target_state_or_region(
                FakeSearchRequest(target_direction="midwest")
            )
        )
        self.assertFalse(
            miss_load.matches_target_state_or_region(
                FakeSearchRequest(target_direction="TX")
            )
        )


if __name__ == "__main__":
    unittest.main()
