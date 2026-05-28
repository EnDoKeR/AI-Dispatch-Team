import unittest

from app.market_intelligence.market_weight_rules import apply_weight_rules


class FakeLoad:
    def __init__(self, weight=0):
        self.weight = weight
        self.is_overweight = False
        self.is_blocked = False
        self.is_review_once = False
        self.block_reasons = []
        self.review_reasons = []


class TestMarketWeightRules(unittest.TestCase):
    def test_apply_weight_rules_does_nothing_when_max_weight_missing(self):
        load = FakeLoad(weight=45000)

        result = apply_weight_rules(load, max_weight=0, equipment="flatbed")

        self.assertIs(result, load)
        self.assertFalse(load.is_overweight)
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)

    def test_apply_weight_rules_does_nothing_when_load_weight_missing(self):
        load = FakeLoad(weight=0)

        apply_weight_rules(load, max_weight=40000, equipment="flatbed")

        self.assertFalse(load.is_overweight)
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)

    def test_apply_weight_rules_does_nothing_when_weight_fits(self):
        load = FakeLoad(weight=39000)

        apply_weight_rules(load, max_weight=40000, equipment="flatbed")

        self.assertFalse(load.is_overweight)
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)

    def test_apply_weight_rules_reviews_overweight_flatbed(self):
        load = FakeLoad(weight=45000)

        apply_weight_rules(load, max_weight=40000, equipment="flatbed")

        self.assertTrue(load.is_overweight)
        self.assertFalse(load.is_blocked)
        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Weight 45000 is above driver setting 40000."],
        )

    def test_apply_weight_rules_blocks_overweight_conestoga(self):
        load = FakeLoad(weight=45000)

        apply_weight_rules(load, max_weight=40000, equipment="conestoga")

        self.assertTrue(load.is_overweight)
        self.assertTrue(load.is_blocked)
        self.assertFalse(load.is_review_once)
        self.assertEqual(
            load.block_reasons,
            ["Weight 45000 is above Conestoga driver setting 40000."],
        )


if __name__ == "__main__":
    unittest.main()
