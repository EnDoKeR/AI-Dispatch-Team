import unittest

from app.market_intelligence.notes_parser_payment import (
    detect_cash_or_zelle,
    detect_quickpay_review,
)


class TestNotesParserPayment(unittest.TestCase):
    def test_detect_cash_or_zelle_blocks_cash_payment_language(self):
        self.assertTrue(detect_cash_or_zelle("cash or zelle"))
        self.assertTrue(detect_cash_or_zelle("zelle or cash"))
        self.assertTrue(detect_cash_or_zelle("cash/zelle"))
        self.assertTrue(detect_cash_or_zelle("cash on delivery"))
        self.assertTrue(detect_cash_or_zelle("zelle"))
        self.assertTrue(detect_cash_or_zelle("cashapp"))
        self.assertTrue(detect_cash_or_zelle("cash app"))

    def test_detect_cash_or_zelle_does_not_block_quickpay(self):
        self.assertFalse(detect_cash_or_zelle("quickpay available"))
        self.assertFalse(detect_cash_or_zelle("quick pay available"))

    def test_detect_quickpay_review_detects_quickpay(self):
        self.assertTrue(detect_quickpay_review("quickpay available"))
        self.assertTrue(detect_quickpay_review("quick pay available"))

    def test_detect_quickpay_review_does_not_detect_clean_text(self):
        self.assertFalse(detect_quickpay_review("normal broker payment"))


if __name__ == "__main__":
    unittest.main()
