import unittest

from app.market_intelligence.market_local_load_rules import apply_local_load_rules


class FakeLoad:
    def __init__(self, loaded_miles=0):
        self.loaded_miles = loaded_miles
        self.is_local_load = False
        self.is_blocked = False
        self.block_reasons = []


class TestMarketLocalLoadRules(unittest.TestCase):
    def test_apply_local_load_rules_blocks_same_origin_and_destination(self):
        load = FakeLoad(loaded_miles=100)

        result = apply_local_load_rules(
            load,
            origin_text="dallas, tx",
            destination_text="dallas, tx",
        )

        self.assertIs(result, load)
        self.assertTrue(load.is_local_load)
        self.assertTrue(load.is_blocked)
        self.assertEqual(load.block_reasons, ["Same pickup and delivery city."])

    def test_apply_local_load_rules_blocks_low_loaded_miles(self):
        load = FakeLoad(loaded_miles=10)

        apply_local_load_rules(
            load,
            origin_text="dallas, tx",
            destination_text="fort worth, tx",
        )

        self.assertTrue(load.is_local_load)
        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["Loaded miles are too low / local load."],
        )

    def test_apply_local_load_rules_can_add_both_reasons(self):
        load = FakeLoad(loaded_miles=5)

        apply_local_load_rules(
            load,
            origin_text="dallas, tx",
            destination_text="dallas, tx",
        )

        self.assertTrue(load.is_local_load)
        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            [
                "Same pickup and delivery city.",
                "Loaded miles are too low / local load.",
            ],
        )

    def test_apply_local_load_rules_does_nothing_for_non_local_load(self):
        load = FakeLoad(loaded_miles=100)

        apply_local_load_rules(
            load,
            origin_text="dallas, tx",
            destination_text="houston, tx",
        )

        self.assertFalse(load.is_local_load)
        self.assertFalse(load.is_blocked)
        self.assertEqual(load.block_reasons, [])


if __name__ == "__main__":
    unittest.main()
