from pathlib import Path
from app.market_intelligence.reload_chain import build_chain_candidates
from app.market_intelligence.load_source import load_market_loads
from app.market_intelligence.search_request import load_search_request
from app.market_intelligence.decision_logger import log_decisions
from app.market_intelligence.driver_profile_loader import apply_driver_profile_to_search_request
from app.market_intelligence.market_snapshot_stats import (
    bucket_stats,
    fit_stats,
    market_recommendation,
)
from app.market_intelligence.market_snapshot_explanation import build_market_explanation
from app.market_intelligence.market_snapshot_opportunities import (
    get_review_once_loads,
    get_top_opportunities,
)
from app.market_intelligence.market_snapshot_route_fallback import prepare_route_fallback
from app.market_intelligence.market_snapshot_builder import (
    apply_search_request,
    build_market_snapshot_context,
)
from app.market_intelligence.market_snapshot_console_report import print_driver_report
from app.market_intelligence.market_snapshot_telegram_dispatcher import (
    send_market_snapshot_to_telegram,
)

SEARCH_REQUESTS_FOLDER = "data/search_requests"


def get_active_search_request_files():
    folder = Path(SEARCH_REQUESTS_FOLDER)

    if not folder.exists():
        return []

    files = []

    for path in folder.glob("*_active.json"):
        files.append(path.name)

    return sorted(files)

def process_search_request(request_file):
    search_request = load_search_request(request_file)
    search_request = apply_driver_profile_to_search_request(search_request)

    search_location = search_request.current_location

    loads = load_market_loads()

    context = build_market_snapshot_context(
        loads=loads,
        search_request=search_request,
        search_location=search_location,
        prepare_route_fallback_func=prepare_route_fallback,
        apply_search_request_func=apply_search_request,
        bucket_stats_func=bucket_stats,
        fit_stats_func=fit_stats,
        market_recommendation_func=market_recommendation,
        build_market_explanation_func=build_market_explanation,
        get_top_opportunities_func=get_top_opportunities,
        get_review_once_loads_func=get_review_once_loads,
        build_chain_candidates_func=build_chain_candidates,
    )

    search_request = context["search_request"]
    loads = context["loads"]
    stats = context["stats"]
    recommendation = context["recommendation"]
    top_opportunities = context["top_opportunities"]
    review_once_loads = context["review_once_loads"]

    decision_log_result = log_decisions(
        search_request=search_request,
        loads=loads,
        recommendation=recommendation,
    )

    print(
        f"Decision log saved for {search_request.driver_name}: "
        f"{decision_log_result['loads_logged']} loads | "
        f"MATCH: {decision_log_result['match_count']} | "
        f"REVIEW_ONCE: {decision_log_result['review_once_count']} | "
        f"BLOCK: {decision_log_result['block_count']} | "
        f"Run ID: {decision_log_result['run_id']}"
    )

    send_market_snapshot_to_telegram(
        stats=stats,
        recommendation=recommendation,
        top_opportunities=top_opportunities,
        review_once_loads=review_once_loads,
        search_request=search_request,
        loads=loads,
        search_location=search_location,
    )


def run_market_snapshot():
    active_requests = get_active_search_request_files()

    if not active_requests:
        print("No active search requests found.")
        print("Create files like data/search_requests/sergey_active.json")
        return

    print(f"Active search requests found: {len(active_requests)}")

    for request_file in active_requests:
        process_search_request(request_file)
