import unittest

from app.market_intelligence.market_snapshot_builder import apply_search_request


class FakeLoad:
    def __init__(self):
        self.applied_request = None

    def apply_search_request(self, search_request):
        self.applied_request = search_request


class MarketSnapshotBuilderTest(unittest.TestCase):
    def test_apply_search_request_applies_request_to_all_loads(self):
        search_request = object()
        loads = [
            FakeLoad(),
            FakeLoad(),
        ]

        result = apply_search_request(loads, search_request)

        self.assertIs(result, loads)
        self.assertIs(loads[0].applied_request, search_request)
        self.assertIs(loads[1].applied_request, search_request)


if __name__ == "__main__":
    unittest.main()
