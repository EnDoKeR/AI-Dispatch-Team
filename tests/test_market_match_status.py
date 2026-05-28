import unittest

from app.market_intelligence.market_match_status import finalize_driver_match, reset_driver_match_state


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



class TestMarketMatchStateReset(unittest.TestCase):
    def test_reset_driver_match_state_clears_match_state(self):
        load = FakeLoad()

        load.match_reasons = ["Old match"]
        load.review_reasons = ["Old review"]
        load.block_reasons = ["Old block"]

        load.is_blocked = True
        load.is_review_once = True
        load.is_clean_match = True

        load.target_relation = "MATCH"
        load.driver_fit_status = "CLEAN_MATCH"
        load.driver_match_status = "MATCH"
        load.driver_match_notes = ["Old notes"]

        result = reset_driver_match_state(load)

        self.assertIs(result, load)
        self.assertEqual(load.match_reasons, [])
        self.assertEqual(load.review_reasons, [])
        self.assertEqual(load.block_reasons, [])

        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)
        self.assertFalse(load.is_clean_match)

        self.assertEqual(load.target_relation, "MISMATCH")
        self.assertEqual(load.driver_fit_status, "UNKNOWN")
        self.assertEqual(load.driver_match_status, "UNKNOWN")
        self.assertEqual(load.driver_match_notes, [])


if __name__ == "__main__":
    unittest.main()
