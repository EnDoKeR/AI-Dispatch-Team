import unittest

from app.market_intelligence.market_snapshot_route_fallback import prepare_route_fallback


class FakeSearchRequest:
    def __init__(self, target_direction_mode="SOFT", driver_name="Alex"):
        self.target_direction_mode = target_direction_mode
        self.driver_name = driver_name
        self.route_fallback_active = None


class FakeLoad:
    def __init__(self, city_match=False, state_or_region_match=False):
        self.city_match = city_match
        self.state_or_region_match = state_or_region_match

    def matches_target_city_radius(self, search_request):
        return self.city_match

    def matches_target_state_or_region(self, search_request):
        return self.state_or_region_match


class TestMarketSnapshotRouteFallback(unittest.TestCase):
    def test_prepare_route_fallback_disables_fallback_when_mode_is_not_target_then_route(self):
        search_request = FakeSearchRequest(target_direction_mode="SOFT")
        loads = [
            FakeLoad(city_match=False, state_or_region_match=False),
        ]

        result = prepare_route_fallback(loads, search_request)

        self.assertIs(result, search_request)
        self.assertFalse(search_request.route_fallback_active)

    def test_prepare_route_fallback_disables_fallback_when_city_target_load_exists(self):
        search_request = FakeSearchRequest(target_direction_mode="TARGET_THEN_ROUTE")
        loads = [
            FakeLoad(city_match=True, state_or_region_match=False),
        ]

        result = prepare_route_fallback(loads, search_request)

        self.assertIs(result, search_request)
        self.assertFalse(search_request.route_fallback_active)

    def test_prepare_route_fallback_disables_fallback_when_state_or_region_target_load_exists(self):
        search_request = FakeSearchRequest(target_direction_mode="TARGET_THEN_ROUTE")
        loads = [
            FakeLoad(city_match=False, state_or_region_match=True),
        ]

        result = prepare_route_fallback(loads, search_request)

        self.assertIs(result, search_request)
        self.assertFalse(search_request.route_fallback_active)

    def test_prepare_route_fallback_enables_fallback_when_no_direct_target_loads_exist(self):
        search_request = FakeSearchRequest(target_direction_mode="TARGET_THEN_ROUTE")
        loads = [
            FakeLoad(city_match=False, state_or_region_match=False),
            FakeLoad(city_match=False, state_or_region_match=False),
        ]

        result = prepare_route_fallback(loads, search_request)

        self.assertIs(result, search_request)
        self.assertTrue(search_request.route_fallback_active)


if __name__ == "__main__":
    unittest.main()
