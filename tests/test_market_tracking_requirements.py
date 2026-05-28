import unittest

from app.market_intelligence.market_tracking_requirements import (
    apply_tracking_requirement,
)


class FakeLoad:
    def __init__(self):
        self.match_reasons = []
        self.block_reasons = []
        self.is_blocked = False


class FakeSearchRequest:
    def __init__(self, driver_tracking_ok=True):
        self.driver_tracking_ok = driver_tracking_ok


class TestMarketTrackingRequirements(unittest.TestCase):
    def test_apply_tracking_requirement_does_nothing_when_not_required(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_tracking_ok=False)

        result = apply_tracking_requirement(
            load,
            search_request,
            "clean flatbed load",
        )

        self.assertIs(result, load)
        self.assertFalse(load.is_blocked)
        self.assertEqual(load.match_reasons, [])
        self.assertEqual(load.block_reasons, [])

    def test_apply_tracking_requirement_matches_when_driver_accepts_tracking(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_tracking_ok=True)

        apply_tracking_requirement(
            load,
            search_request,
            "tracking required",
        )

        self.assertFalse(load.is_blocked)
        self.assertEqual(
            load.match_reasons,
            ["Tracking is accepted by driver profile."],
        )

    def test_apply_tracking_requirement_detects_macro_point(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_tracking_ok=True)

        apply_tracking_requirement(
            load,
            search_request,
            "macro point required",
        )

        self.assertEqual(
            load.match_reasons,
            ["Tracking is accepted by driver profile."],
        )

    def test_apply_tracking_requirement_detects_macropoint(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_tracking_ok=True)

        apply_tracking_requirement(
            load,
            search_request,
            "macropoint setup needed",
        )

        self.assertEqual(
            load.match_reasons,
            ["Tracking is accepted by driver profile."],
        )

    def test_apply_tracking_requirement_blocks_when_driver_rejects_tracking(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_tracking_ok=False)

        apply_tracking_requirement(
            load,
            search_request,
            "tracking required",
        )

        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["Tracking required, but driver profile says tracking is not accepted."],
        )


if __name__ == "__main__":
    unittest.main()
