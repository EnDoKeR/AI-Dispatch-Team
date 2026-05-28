import unittest

from app.market_intelligence.market_match_status import finalize_driver_match


class FakeLoad:
    def __init__(self):
        self.is_blocked = False
        self.is_review_once = False
        self.is_clean_match = False

        self.driver_fit_status = "UNKNOWN"
        self.driver_match_status = "UNKNOWN"
        self.driver_match_notes = []

        self.block_reasons = []
        self.review_reasons = []
        self.match_reasons = []


class TestMarketMatchStatus(unittest.TestCase):
    def test_finalize_driver_match_sets_block_status(self):
        load = FakeLoad()
        load.is_blocked = True
        load.is_review_once = True
        load.block_reasons = ["Too heavy"]

        result = finalize_driver_match(load)

        self.assertIs(result, load)
        self.assertEqual(load.driver_fit_status, "BLOCKED")
        self.assertEqual(load.driver_match_status, "BLOCK")
        self.assertEqual(load.driver_match_notes, ["Too heavy"])
        self.assertFalse(load.is_clean_match)

    def test_finalize_driver_match_sets_review_once_status(self):
        load = FakeLoad()
        load.is_review_once = True
        load.review_reasons = ["Rate check"]

        result = finalize_driver_match(load)

        self.assertIs(result, load)
        self.assertEqual(load.driver_fit_status, "REVIEW_ONCE")
        self.assertEqual(load.driver_match_status, "REVIEW_ONCE")
        self.assertEqual(load.driver_match_notes, ["Rate check"])
        self.assertFalse(load.is_clean_match)

    def test_finalize_driver_match_sets_clean_match_status(self):
        load = FakeLoad()
        load.match_reasons = ["Clean fit"]

        result = finalize_driver_match(load)

        self.assertIs(result, load)
        self.assertEqual(load.driver_fit_status, "CLEAN_MATCH")
        self.assertEqual(load.driver_match_status, "MATCH")
        self.assertEqual(load.driver_match_notes, ["Clean fit"])
        self.assertTrue(load.is_clean_match)


if __name__ == "__main__":
    unittest.main()
