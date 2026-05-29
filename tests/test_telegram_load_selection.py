import unittest
from unittest.mock import patch

from app.market_intelligence.telegram_duplicate_keys import load_duplicate_key
from app.market_intelligence.telegram_load_selection import select_new_loads


class FakeLoad:
    def __init__(
        self,
        pickup="Dallas, TX",
        delivery="Houston, TX",
        rate=2200,
        loaded_miles=240,
        broker="Test Broker",
        pickup_date="2026-05-28",
    ):
        self.pickup = pickup
        self.delivery = delivery
        self.rate = rate
        self.loaded_miles = loaded_miles
        self.broker = broker
        self.pickup_date = pickup_date


class FakeSearchRequest:
    driver_name = "Alex"


class TestTelegramLoadSelection(unittest.TestCase):
    def test_select_new_loads_removes_duplicates_before_limit(self):
        search_request = FakeSearchRequest()
        first = FakeLoad(rate=2200)
        duplicate = FakeLoad(rate=2200)
        second = FakeLoad(rate=2500)

        with patch("builtins.print"):
            result = select_new_loads(
                [first, duplicate, second],
                search_request,
                sent_history=set(),
                limit=2,
            )

        self.assertEqual(result["selected_loads"], [first, second])
        self.assertEqual(result["loads_to_send"], [first, second])
        self.assertEqual(result["already_sent_loads"], [])

    def test_select_new_loads_filters_already_sent_loads(self):
        search_request = FakeSearchRequest()
        first = FakeLoad(rate=2200)
        second = FakeLoad(rate=2500)
        sent_history = {
            load_duplicate_key(
                first,
                driver_name=search_request.driver_name,
            )
        }

        result = select_new_loads(
            [first, second],
            search_request,
            sent_history=sent_history,
            limit=3,
        )

        self.assertEqual(result["selected_loads"], [first, second])
        self.assertEqual(result["already_sent_loads"], [first])
        self.assertEqual(result["loads_to_send"], [second])

    def test_select_new_loads_applies_limit_after_deduplication(self):
        search_request = FakeSearchRequest()
        first = FakeLoad(rate=2200)
        duplicate = FakeLoad(rate=2200)
        second = FakeLoad(rate=2500)
        third = FakeLoad(rate=2600)

        with patch("builtins.print"):
            result = select_new_loads(
                [first, duplicate, second, third],
                search_request,
                sent_history=set(),
                limit=2,
            )

        self.assertEqual(result["selected_loads"], [first, second])
        self.assertEqual(result["loads_to_send"], [first, second])


if __name__ == "__main__":
    unittest.main()
