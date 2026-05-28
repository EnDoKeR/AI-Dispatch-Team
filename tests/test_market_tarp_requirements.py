import unittest

from app.market_intelligence.market_tarp_requirements import (
    apply_tarps_requirement,
    detect_tarps_requirement,
    get_tarp_size_feet,
)


class FakeLoad:
    def __init__(self):
        self.match_reasons = []
        self.review_reasons = []
        self.block_reasons = []
        self.is_review_once = False
        self.is_blocked = False


class FakeSearchRequest:
    def __init__(
        self,
        equipment="Flatbed",
        driver_can_take_tarps=None,
        driver_max_tarp_size="",
    ):
        self.equipment = equipment
        self.driver_can_take_tarps = driver_can_take_tarps
        self.driver_max_tarp_size = driver_max_tarp_size


class TestMarketTarpRequirements(unittest.TestCase):
    def test_get_tarp_size_feet_detects_size(self):
        self.assertEqual(get_tarp_size_feet("8 ft tarps required"), 8)
        self.assertEqual(get_tarp_size_feet("6ft tarps"), 6)
        self.assertEqual(get_tarp_size_feet("tarps required"), 0)

    def test_detect_tarps_requirement_returns_false_for_no_tarp_terms(self):
        self.assertEqual(detect_tarps_requirement("No tarps required"), (False, 0))
        self.assertEqual(detect_tarps_requirement("tarp not required"), (False, 0))

    def test_detect_tarps_requirement_detects_required_size(self):
        self.assertEqual(detect_tarps_requirement("8 ft tarps required"), (True, 8))
        self.assertEqual(detect_tarps_requirement("needs 6ft tarps"), (True, 6))

    def test_detect_tarps_requirement_detects_generic_requirement(self):
        self.assertEqual(detect_tarps_requirement("tarps required"), (True, 0))
        self.assertEqual(detect_tarps_requirement("must tarp"), (True, 0))

    def test_detect_tarps_requirement_returns_none_when_not_mentioned(self):
        self.assertEqual(detect_tarps_requirement("clean flatbed load"), (None, 0))

    def test_apply_tarps_requirement_does_nothing_when_not_required(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_can_take_tarps=False)

        result = apply_tarps_requirement(load, search_request, "clean flatbed load")

        self.assertIs(result, load)
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)
        self.assertEqual(load.match_reasons, [])
        self.assertEqual(load.review_reasons, [])
        self.assertEqual(load.block_reasons, [])

    def test_apply_tarps_requirement_conestoga_covers_tarps(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(equipment="Conestoga")

        apply_tarps_requirement(load, search_request, "8 ft tarps required")

        self.assertEqual(
            load.match_reasons,
            ["8 ft tarp requirement covered by Conestoga."],
        )
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)

    def test_apply_tarps_requirement_driver_accepts_tarps(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(
            equipment="Flatbed",
            driver_can_take_tarps=True,
            driver_max_tarp_size="8 ft",
        )

        apply_tarps_requirement(load, search_request, "6 ft tarps required")

        self.assertEqual(
            load.match_reasons,
            ["6 ft tarps accepted by driver profile."],
        )
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)

    def test_apply_tarps_requirement_review_when_required_size_above_driver_max(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(
            equipment="Flatbed",
            driver_can_take_tarps=True,
            driver_max_tarp_size="4 ft",
        )

        apply_tarps_requirement(load, search_request, "8 ft tarps required")

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["8 ft tarps required, but driver max tarp size is 4 ft."],
        )

    def test_apply_tarps_requirement_blocks_when_driver_cannot_take_tarps(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(
            equipment="Flatbed",
            driver_can_take_tarps=False,
        )

        apply_tarps_requirement(load, search_request, "8 ft tarps required")

        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["8 ft tarps required, but driver profile says driver cannot take tarps."],
        )

    def test_apply_tarps_requirement_review_when_driver_answer_unknown(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(equipment="Flatbed")

        apply_tarps_requirement(load, search_request, "tarps required")

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Tarps required; ask driver and save answer in driver profile."],
        )


if __name__ == "__main__":
    unittest.main()
