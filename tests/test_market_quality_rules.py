import unittest

from app.market_intelligence.market_quality_rules import (
    apply_empty_miles_rule,
    apply_quality_rules,
    apply_rate_check_rule,
    apply_rpm_quality_rule,
)


class FakeLoad:
    def __init__(self, rate=1000, empty_miles=0, total_rpm=0):
        self.rate = rate
        self.empty_miles = empty_miles
        self.total_rpm = total_rpm

        self.is_too_far_empty = False
        self.is_review_once = False
        self.is_low_rpm = False

        self.review_reasons = []
        self.match_reasons = []


class TestMarketQualityRules(unittest.TestCase):
    def test_apply_empty_miles_rule_reviews_when_empty_above_max(self):
        load = FakeLoad(empty_miles=300)

        apply_empty_miles_rule(load, max_empty=200)

        self.assertTrue(load.is_too_far_empty)
        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Empty miles 300 are above driver setting 200."],
        )

    def test_apply_empty_miles_rule_does_nothing_when_empty_fits(self):
        load = FakeLoad(empty_miles=100)

        apply_empty_miles_rule(load, max_empty=200)

        self.assertFalse(load.is_too_far_empty)
        self.assertFalse(load.is_review_once)
        self.assertEqual(load.review_reasons, [])

    def test_apply_rate_check_rule_reviews_missing_rate(self):
        load = FakeLoad(rate=0)

        apply_rate_check_rule(load)

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Rate is missing / posted as $0; dispatcher should check rate with broker."],
        )

    def test_apply_rate_check_rule_does_nothing_when_rate_exists(self):
        load = FakeLoad(rate=2500)

        apply_rate_check_rule(load)

        self.assertFalse(load.is_review_once)
        self.assertEqual(load.review_reasons, [])

    def test_apply_rpm_quality_rule_adds_quality_warning(self):
        load = FakeLoad(total_rpm=1.95)

        apply_rpm_quality_rule(load, min_total_rpm=2.5)

        self.assertTrue(load.is_low_rpm)
        self.assertEqual(
            load.match_reasons,
            ["RPM $1.95 is below preferred minimum $2.5."],
        )

    def test_apply_rpm_quality_rule_does_not_block_or_review(self):
        load = FakeLoad(total_rpm=1.95)

        apply_rpm_quality_rule(load, min_total_rpm=2.5)

        self.assertFalse(load.is_review_once)

    def test_apply_quality_rules_applies_all_quality_checks(self):
        load = FakeLoad(rate=0, empty_miles=300, total_rpm=1.95)

        result = apply_quality_rules(
            load,
            max_empty=200,
            min_total_rpm=2.5,
        )

        self.assertIs(result, load)
        self.assertTrue(load.is_too_far_empty)
        self.assertTrue(load.is_review_once)
        self.assertTrue(load.is_low_rpm)
        self.assertEqual(
            load.review_reasons,
            [
                "Empty miles 300 are above driver setting 200.",
                "Rate is missing / posted as $0; dispatcher should check rate with broker.",
            ],
        )
        self.assertEqual(
            load.match_reasons,
            ["RPM $1.95 is below preferred minimum $2.5."],
        )


if __name__ == "__main__":
    unittest.main()
