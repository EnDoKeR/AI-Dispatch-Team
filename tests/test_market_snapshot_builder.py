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


class MarketSnapshotContextBuilderTest(unittest.TestCase):
    def test_build_market_snapshot_context_returns_expected_context(self):
        from app.market_intelligence.market_snapshot_builder import (
            build_market_snapshot_context,
        )

        class FakeLoad:
            def __init__(self, name):
                self.name = name
                self.applied_request = None

            def apply_search_request(self, search_request):
                self.applied_request = search_request

        search_request = object()
        search_location = "Dallas, TX"
        loads = [
            FakeLoad("one"),
            FakeLoad("two"),
        ]

        stats_result = {"stats": True}
        fit_result = {"fit": True}
        recommendation_result = {
            "best_bucket": "700-1300",
            "market_activity": "MEDIUM",
        }
        explanation_result = ["Market explanation"]
        top_result = [loads[0]]
        review_result = [loads[1]]
        chain_result = [{"chain": True}]

        context = build_market_snapshot_context(
            loads=loads,
            search_request=search_request,
            search_location=search_location,
            prepare_route_fallback_func=lambda input_loads, input_request: input_request,
            apply_search_request_func=lambda input_loads, input_request: input_loads,
            bucket_stats_func=lambda input_loads: stats_result,
            fit_stats_func=lambda input_loads: fit_result,
            market_recommendation_func=lambda stats, fit: recommendation_result,
            build_market_explanation_func=lambda stats, recommendation: explanation_result,
            get_top_opportunities_func=lambda input_loads: top_result,
            get_review_once_loads_func=lambda input_loads: review_result,
            build_chain_candidates_func=lambda input_loads, input_request, limit: chain_result,
        )

        self.assertIs(context["search_request"], search_request)
        self.assertEqual(context["search_location"], search_location)
        self.assertIs(context["loads"], loads)
        self.assertIs(context["stats"], stats_result)
        self.assertIs(context["fit"], fit_result)
        self.assertIs(context["recommendation"], recommendation_result)
        self.assertIs(context["explanation"], explanation_result)
        self.assertIs(context["top_opportunities"], top_result)
        self.assertIs(context["review_once_loads"], review_result)
        self.assertIs(context["chain_candidates"], chain_result)


if __name__ == "__main__":
    unittest.main()
