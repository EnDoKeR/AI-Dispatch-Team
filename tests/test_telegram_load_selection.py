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

    def test_select_new_loads_continues_past_already_sent_top_loads(self):
        search_request = FakeSearchRequest()
        sent_first = FakeLoad(rate=2200)
        sent_second = FakeLoad(rate=2300)
        sent_third = FakeLoad(rate=2400)
        unsent_fourth = FakeLoad(rate=2500)
        unsent_fifth = FakeLoad(rate=2600)
        unsent_sixth = FakeLoad(rate=2700)
        sent_history = {
            load_duplicate_key(
                load,
                driver_name=search_request.driver_name,
            )
            for load in [sent_first, sent_second, sent_third]
        }

        result = select_new_loads(
            [
                sent_first,
                sent_second,
                sent_third,
                unsent_fourth,
                unsent_fifth,
                unsent_sixth,
            ],
            search_request,
            sent_history=sent_history,
            limit=2,
        )

        self.assertEqual(
            result["selected_loads"],
            [sent_first, sent_second, sent_third, unsent_fourth, unsent_fifth],
        )
        self.assertEqual(
            result["already_sent_loads"],
            [sent_first, sent_second, sent_third],
        )
        self.assertEqual(result["loads_to_send"], [unsent_fourth, unsent_fifth])

    def test_select_new_loads_limit_applies_to_unsent_loads(self):
        search_request = FakeSearchRequest()
        sent_first = FakeLoad(rate=2200)
        sent_second = FakeLoad(rate=2300)
        unsent_first = FakeLoad(rate=2400)
        unsent_second = FakeLoad(rate=2500)
        unsent_third = FakeLoad(rate=2600)
        sent_history = {
            load_duplicate_key(
                load,
                driver_name=search_request.driver_name,
            )
            for load in [sent_first, sent_second]
        }

        result = select_new_loads(
            [
                sent_first,
                sent_second,
                unsent_first,
                unsent_second,
                unsent_third,
            ],
            search_request,
            sent_history=sent_history,
            limit=2,
        )

        self.assertEqual(
            result["selected_loads"],
            [sent_first, sent_second, unsent_first, unsent_second],
        )
        self.assertEqual(result["already_sent_loads"], [sent_first, sent_second])
        self.assertEqual(result["loads_to_send"], [unsent_first, unsent_second])

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
