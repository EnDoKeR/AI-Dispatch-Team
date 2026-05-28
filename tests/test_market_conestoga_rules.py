import unittest

from app.market_intelligence.market_conestoga_rules import apply_conestoga_rules


class FakeLoad:
    def __init__(self):
        self.is_blocked = False
        self.is_review_once = False
        self.block_reasons = []
        self.review_reasons = []


class TestMarketConestogaRules(unittest.TestCase):
    def test_apply_conestoga_rules_does_nothing_for_non_conestoga_equipment(self):
        load = FakeLoad()

        result = apply_conestoga_rules(
            load,
            equipment="flatbed",
            notes_lower="no conestoga",
            posted_lower="flatbed",
        )

        self.assertIs(result, load)
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)
        self.assertEqual(load.block_reasons, [])
        self.assertEqual(load.review_reasons, [])

    def test_apply_conestoga_rules_blocks_when_notes_say_no_conestoga(self):
        load = FakeLoad()

        apply_conestoga_rules(
            load,
            equipment="conestoga",
            notes_lower="no conestoga accepted",
            posted_lower="flatbed",
        )

        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["Notes say Conestoga is not accepted."],
        )

    def test_apply_conestoga_rules_blocks_when_notes_say_no_stoga(self):
        load = FakeLoad()

        apply_conestoga_rules(
            load,
            equipment="conestoga",
            notes_lower="no stoga",
            posted_lower="flatbed",
        )

        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["Notes say Conestoga is not accepted."],
        )

    def test_apply_conestoga_rules_reviews_flatbed_posting(self):
        load = FakeLoad()

        apply_conestoga_rules(
            load,
            equipment="conestoga",
            notes_lower="clean load",
            posted_lower="flatbed",
        )

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Posted as Flatbed/Step Deck; Conestoga must be verified."],
        )
        self.assertFalse(load.is_blocked)

    def test_apply_conestoga_rules_reviews_step_deck_posting(self):
        load = FakeLoad()

        apply_conestoga_rules(
            load,
            equipment="conestoga",
            notes_lower="clean load",
            posted_lower="step deck",
        )

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Posted as Flatbed/Step Deck; Conestoga must be verified."],
        )

    def test_apply_conestoga_rules_reviews_short_flatbed_codes(self):
        for posted_lower in ["f", "fd", "ft"]:
            load = FakeLoad()

            apply_conestoga_rules(
                load,
                equipment="conestoga",
                notes_lower="clean load",
                posted_lower=posted_lower,
            )

            self.assertTrue(load.is_review_once)
            self.assertEqual(
                load.review_reasons,
                ["Posted as Flatbed/Step Deck; Conestoga must be verified."],
            )

    def test_apply_conestoga_rules_does_nothing_for_clean_conestoga_posting(self):
        load = FakeLoad()

        apply_conestoga_rules(
            load,
            equipment="conestoga",
            notes_lower="clean load",
            posted_lower="conestoga",
        )

        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)
        self.assertEqual(load.block_reasons, [])
        self.assertEqual(load.review_reasons, [])


if __name__ == "__main__":
    unittest.main()
