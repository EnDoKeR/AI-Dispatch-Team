def apply_search_request(loads, search_request):
    for load in loads:
        load.apply_search_request(search_request)

    return loads


def build_market_snapshot_context(
    loads,
    search_request,
    search_location="",
    prepare_route_fallback_func=None,
    apply_search_request_func=None,
    bucket_stats_func=None,
    fit_stats_func=None,
    market_recommendation_func=None,
    build_market_explanation_func=None,
    get_top_opportunities_func=None,
    get_review_once_loads_func=None,
    build_chain_candidates_func=None,
):
    search_request = prepare_route_fallback_func(
        loads,
        search_request,
    )

    loads = apply_search_request_func(
        loads,
        search_request,
    )

    stats = bucket_stats_func(loads)
    fit = fit_stats_func(loads)

    recommendation = market_recommendation_func(
        stats,
        fit,
    )

    explanation = build_market_explanation_func(
        stats,
        recommendation,
    )

    top_opportunities = get_top_opportunities_func(loads)
    review_once_loads = get_review_once_loads_func(loads)

    chain_candidates = build_chain_candidates_func(
        loads,
        search_request,
        limit=5,
    )

    return {
        "search_request": search_request,
        "search_location": search_location,
        "loads": loads,
        "stats": stats,
        "fit": fit,
        "recommendation": recommendation,
        "explanation": explanation,
        "top_opportunities": top_opportunities,
        "review_once_loads": review_once_loads,
        "chain_candidates": chain_candidates,
    }

