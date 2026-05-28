import unittest
from unittest.mock import patch

from app.market_intelligence.market_broker_memory import apply_broker_memory


class FakeLoad:
    def __init__(self, broker_mc="123456"):
        self.broker_mc = broker_mc
        self.is_review_once = False
        self.review_reasons = []
        self.match_reasons = []


class TestMarketBrokerMemory(unittest.TestCase):
    def test_apply_broker_memory_does_nothing_when_mc_missing(self):
        load = FakeLoad(broker_mc="")

        result = apply_broker_memory(load)

        self.assertIs(result, load)
        self.assertFalse(load.is_review_once)
        self.assertEqual(load.review_reasons, [])
        self.assertEqual(load.match_reasons, [])

    def test_apply_broker_memory_does_nothing_for_invalid_mc_values(self):
        for broker_mc in ["NEEDS CHECK", "NO MC", "UNKNOWN", "NONE"]:
            load = FakeLoad(broker_mc=broker_mc)

            apply_broker_memory(load)

            self.assertFalse(load.is_review_once)
            self.assertEqual(load.review_reasons, [])
            self.assertEqual(load.match_reasons, [])

    @patch("app.market_intelligence.market_broker_memory.get_broker_memory_status")
    def test_apply_broker_memory_reviews_bad_broker(self, mock_status):
        mock_status.return_value = {
            "status": "BAD_BROKER_REVIEW",
            "risk_level": "HIGH",
            "reasons": ["previous rejection", "bad feedback"],
        }
        load = FakeLoad(broker_mc="123456")

        apply_broker_memory(load)

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Broker memory requires review: previous rejection; bad feedback. Risk: HIGH."],
        )

    @patch("app.market_intelligence.market_broker_memory.get_broker_memory_status")
    def test_apply_broker_memory_reviews_rate_negotiation_required(self, mock_status):
        mock_status.return_value = {
            "status": "RATE_NEGOTIATION_REQUIRED",
            "risk_level": "MEDIUM",
            "reasons": ["lowball offers"],
        }
        load = FakeLoad(broker_mc="123456")

        apply_broker_memory(load)

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Broker memory shows rate negotiation risk: lowball offers. Risk: MEDIUM."],
        )

    @patch("app.market_intelligence.market_broker_memory.get_broker_memory_status")
    def test_apply_broker_memory_reviews_watchlist(self, mock_status):
        mock_status.return_value = {
            "status": "WATCHLIST",
            "risk_level": "MEDIUM",
            "reasons": ["slow response"],
        }
        load = FakeLoad(broker_mc="123456")

        apply_broker_memory(load)

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Broker memory watchlist: slow response. Risk: MEDIUM."],
        )

    @patch("app.market_intelligence.market_broker_memory.get_broker_memory_status")
    def test_apply_broker_memory_adds_good_signal(self, mock_status):
        mock_status.return_value = {
            "status": "GOOD",
            "risk_level": "LOW",
            "reasons": ["paid fast", "good communication"],
        }
        load = FakeLoad(broker_mc="123456")

        apply_broker_memory(load)

        self.assertFalse(load.is_review_once)
        self.assertEqual(
            load.match_reasons,
            ["Broker memory positive signal: paid fast; good communication."],
        )

    @patch("app.market_intelligence.market_broker_memory.get_broker_memory_status")
    def test_apply_broker_memory_good_without_reasons_does_nothing(self, mock_status):
        mock_status.return_value = {
            "status": "GOOD",
            "risk_level": "LOW",
            "reasons": [],
        }
        load = FakeLoad(broker_mc="123456")

        apply_broker_memory(load)

        self.assertFalse(load.is_review_once)
        self.assertEqual(load.match_reasons, [])


if __name__ == "__main__":
    unittest.main()
