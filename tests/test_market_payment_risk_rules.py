import unittest

from app.market_intelligence.market_payment_risk_rules import apply_payment_risk_rules


class FakeLoad:
    def __init__(self):
        self.is_blocked = False
        self.block_reasons = []


class TestMarketPaymentRiskRules(unittest.TestCase):
    def test_apply_payment_risk_rules_does_nothing_for_clean_text(self):
        load = FakeLoad()

        result = apply_payment_risk_rules(load, "normal broker payment")

        self.assertIs(result, load)
        self.assertFalse(load.is_blocked)
        self.assertEqual(load.block_reasons, [])

    def test_apply_payment_risk_rules_blocks_cash_or_zelle(self):
        load = FakeLoad()

        apply_payment_risk_rules(load, "payment cash or zelle only")

        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["Cash/Zelle type payment detected; likely no-buy / risky broker payment."],
        )

    def test_apply_payment_risk_rules_blocks_cash_zelle(self):
        load = FakeLoad()

        apply_payment_risk_rules(load, "cash/zelle payment")

        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["Cash/Zelle type payment detected; likely no-buy / risky broker payment."],
        )

    def test_apply_payment_risk_rules_blocks_cashapp_cash_app_zelle_and_venmo(self):
        for text in ["cashapp", "cash app", "zelle", "venmo"]:
            load = FakeLoad()

            apply_payment_risk_rules(load, text)

            self.assertTrue(load.is_blocked)
            self.assertEqual(
                load.block_reasons,
                ["Cash/Zelle type payment detected; likely no-buy / risky broker payment."],
            )


if __name__ == "__main__":
    unittest.main()
