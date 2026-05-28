import unittest

from app.market_intelligence.market_direction_matcher import apply_direction_match


class FakeLoad:
    def __init__(
        self,
        matches_city=False,
        matches_target=False,
        should_block=True,
        along_route=False,
        review_reason="",
    ):
        self._matches_city = matches_city
        self._matches_target = matches_target
        self._should_block = should_block
        self._along_route = along_route
        self._review_reason = review_reason

        self.target_relation = "MISMATCH"
        self.match_reasons = []
        self.review_reasons = []
        self.block_reasons = []
        self.is_blocked = False
        self.is_review_once = False

    def matches_target_city_radius(self, search_request):
        return self._matches_city

    def delivery_matches_target(self, search_request):
        return self._matches_target

    def off_target_review_reason(self, search_request):
        return self._review_reason

    def should_block_off_target(self, search_request):
        return self._should_block

    def delivery_is_along_route(self, search_request):
        return self._along_route


class FakeSearchRequest:
    def __init__(self, target_direction="TX"):
        self.target_direction = target_direction


class TestMarketDirectionMatcher(unittest.TestCase):
    def test_apply_direction_match_matches_target_city(self):
        load = FakeLoad(matches_city=True)
        search_request = FakeSearchRequest(target_direction="TX")

        result = apply_direction_match(load, search_request)

        self.assertIs(result, load)
        self.assertEqual(load.target_relation, "MATCH")
        self.assertEqual(load.match_reasons, ["Destination matches target city."])
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)

    def test_apply_direction_match_matches_target_state(self):
        load = FakeLoad(matches_target=True)
        search_request = FakeSearchRequest(target_direction="TX")

        apply_direction_match(load, search_request)

        self.assertEqual(load.target_relation, "MATCH")
        self.assertEqual(load.match_reasons, ["Destination matches target state/region."])
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)

    def test_apply_direction_match_blocks_off_target_load(self):
        load = FakeLoad(
            should_block=True,
            review_reason="Delivery does not match target direction: TX.",
        )
        search_request = FakeSearchRequest(target_direction="TX")

        apply_direction_match(load, search_request)

        self.assertEqual(load.target_relation, "MISMATCH")
        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["Delivery does not match target direction: TX."],
        )
        self.assertFalse(load.is_review_once)

    def test_apply_direction_match_reviews_along_route_load(self):
        load = FakeLoad(
            should_block=False,
            along_route=True,
            review_reason="Load is along route toward TX.",
        )
        search_request = FakeSearchRequest(target_direction="TX")

        apply_direction_match(load, search_request)

        self.assertEqual(load.target_relation, "ALONG_ROUTE")
        self.assertTrue(load.is_review_once)
        self.assertEqual(load.review_reasons, ["Load is along route toward TX."])
        self.assertFalse(load.is_blocked)

    def test_apply_direction_match_reviews_off_target_exception(self):
        load = FakeLoad(
            should_block=False,
            along_route=False,
            review_reason="Strong off-target exception.",
        )
        search_request = FakeSearchRequest(target_direction="TX")

        apply_direction_match(load, search_request)

        self.assertEqual(load.target_relation, "OFF_TARGET_EXCEPTION")
        self.assertTrue(load.is_review_once)
        self.assertEqual(load.review_reasons, ["Strong off-target exception."])
        self.assertFalse(load.is_blocked)

    def test_apply_direction_match_does_not_add_empty_review_reason(self):
        load = FakeLoad(
            should_block=False,
            along_route=True,
            review_reason="",
        )
        search_request = FakeSearchRequest(target_direction="TX")

        apply_direction_match(load, search_request)

        self.assertEqual(load.target_relation, "ALONG_ROUTE")
        self.assertTrue(load.is_review_once)
        self.assertEqual(load.review_reasons, [])


if __name__ == "__main__":
    unittest.main()
