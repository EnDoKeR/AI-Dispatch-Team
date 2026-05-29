import unittest

from app.market_intelligence.telegram_chain_formatter import chain_duplicate_key
from app.market_intelligence.telegram_chain_selection import select_new_chain_candidates


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


def build_candidate(first_rate=2200, reload_rate=2500):
    first_load = FakeLoad(
        pickup="Dallas, TX",
        delivery="Denver, CO",
        rate=first_rate,
    )
    reload_load = FakeLoad(
        pickup="Denver, CO",
        delivery="Houston, TX",
        rate=reload_rate,
    )

    return {
        "first_load": first_load,
        "reload_load": reload_load,
        "chain_data": {
            "total_gross": first_rate + reload_rate,
            "total_miles": 1000,
            "total_rpm": 4.7,
            "chain_score": 85,
        },
    }


class TestTelegramChainSelection(unittest.TestCase):
    def test_select_new_chain_candidates_applies_limit(self):
        search_request = FakeSearchRequest()
        first = build_candidate(first_rate=2200)
        second = build_candidate(first_rate=2300)
        third = build_candidate(first_rate=2400)

        result = select_new_chain_candidates(
            [first, second, third],
            search_request,
            sent_history=set(),
            limit=2,
        )

        self.assertEqual(result["selected_candidates"], [first, second])
        self.assertEqual(result["candidates_to_send"], [first, second])

    def test_select_new_chain_candidates_tracks_duplicates_in_current_run(self):
        search_request = FakeSearchRequest()
        first = build_candidate(first_rate=2200)
        duplicate = build_candidate(first_rate=2200)
        unique = build_candidate(first_rate=2300)

        result = select_new_chain_candidates(
            [first, duplicate, unique],
            search_request,
            sent_history=set(),
            limit=3,
        )

        self.assertEqual(result["duplicate_candidates"], [duplicate])
        self.assertEqual(result["already_sent_candidates"], [])
        self.assertEqual(result["candidates_to_send"], [first, unique])

    def test_select_new_chain_candidates_tracks_already_sent_history(self):
        search_request = FakeSearchRequest()
        already_sent = build_candidate(first_rate=2200)
        fresh = build_candidate(first_rate=2300)
        sent_history = {
            chain_duplicate_key(
                already_sent,
                search_request,
            )
        }

        result = select_new_chain_candidates(
            [already_sent, fresh],
            search_request,
            sent_history=sent_history,
            limit=3,
        )

        self.assertEqual(result["duplicate_candidates"], [])
        self.assertEqual(result["already_sent_candidates"], [already_sent])
        self.assertEqual(result["candidates_to_send"], [fresh])


if __name__ == "__main__":
    unittest.main()
