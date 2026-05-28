import unittest

from app.market_intelligence.market_region_conflict import (
    pickup_region_conflict_with_driver,
)


class FakeLoad:
    def __init__(self, pickup="", origin="", empty_miles=0):
        self.pickup = pickup
        self.origin = origin
        self.empty_miles = empty_miles


class FakeSearchRequest:
    def __init__(self, current_location=""):
        self.current_location = current_location


class TestMarketRegionConflict(unittest.TestCase):
    def test_no_conflict_when_driver_and_pickup_same_state(self):
        load = FakeLoad(pickup="Austin, TX", empty_miles=45)
        search_request = FakeSearchRequest(current_location="Dallas, TX")

        self.assertFalse(pickup_region_conflict_with_driver(load, search_request))

    def test_no_conflict_when_pickup_is_neighbor_state(self):
        load = FakeLoad(pickup="Oklahoma City, OK", empty_miles=45)
        search_request = FakeSearchRequest(current_location="Dallas, TX")

        self.assertFalse(pickup_region_conflict_with_driver(load, search_request))

    def test_conflict_when_states_far_and_empty_miles_low(self):
        load = FakeLoad(pickup="Lakeland, FL", empty_miles=45)
        search_request = FakeSearchRequest(current_location="Stockton, CA")

        self.assertTrue(pickup_region_conflict_with_driver(load, search_request))

    def test_no_conflict_when_states_far_but_empty_miles_high(self):
        load = FakeLoad(pickup="Lakeland, FL", empty_miles=900)
        search_request = FakeSearchRequest(current_location="Stockton, CA")

        self.assertFalse(pickup_region_conflict_with_driver(load, search_request))

    def test_no_conflict_when_location_or_state_missing(self):
        self.assertFalse(
            pickup_region_conflict_with_driver(
                FakeLoad(pickup="", empty_miles=45),
                FakeSearchRequest(current_location="Stockton, CA"),
            )
        )
        self.assertFalse(
            pickup_region_conflict_with_driver(
                FakeLoad(pickup="Lakeland", empty_miles=45),
                FakeSearchRequest(current_location="Stockton, CA"),
            )
        )
        self.assertFalse(
            pickup_region_conflict_with_driver(
                FakeLoad(pickup="Lakeland, FL", empty_miles=45),
                FakeSearchRequest(current_location=""),
            )
        )

    def test_uses_origin_when_pickup_is_missing(self):
        load = FakeLoad(origin="Lakeland, FL", empty_miles=45)
        search_request = FakeSearchRequest(current_location="Stockton, CA")

        self.assertTrue(pickup_region_conflict_with_driver(load, search_request))


if __name__ == "__main__":
    unittest.main()
