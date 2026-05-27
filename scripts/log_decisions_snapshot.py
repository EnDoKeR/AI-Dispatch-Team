import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.decision_logger import log_decisions
from app.market_intelligence.driver_profile_loader import apply_driver_profile_to_search_request
from app.market_intelligence.load_source import load_market_loads
from app.market_intelligence.market_snapshot import (
    apply_search_request,
    bucket_stats,
    fit_stats,
    get_active_search_request_files,
    market_recommendation,
    prepare_route_fallback,
)
from app.market_intelligence.search_request import load_search_request


def log_current_decision_snapshot():
    active_requests = get_active_search_request_files()

    if not active_requests:
        print("No active search requests found.")
        return

    print(f"Active search requests found: {len(active_requests)}")

    total_logged = 0

    for request_file in active_requests:
        print(f"\nLogging decisions for: {request_file}")

        search_request = load_search_request(request_file)
        search_request = apply_driver_profile_to_search_request(search_request)

        loads = load_market_loads()

        search_request = prepare_route_fallback(
            loads,
            search_request,
        )

        loads = apply_search_request(
            loads,
            search_request,
        )

        stats = bucket_stats(loads)
        fit = fit_stats(loads)

        recommendation = market_recommendation(
            stats,
            fit,
        )

        result = log_decisions(
            search_request=search_request,
            loads=loads,
            recommendation=recommendation,
        )

        total_logged += result["loads_logged"]

        print(
            f"Logged {result['loads_logged']} decisions | "
            f"MATCH: {result['match_count']} | "
            f"REVIEW_ONCE: {result['review_once_count']} | "
            f"BLOCK: {result['block_count']} | "
            f"Run ID: {result['run_id']}"
        )

    print("\nDecision logging completed.")
    print(f"Total decisions logged: {total_logged}")
    print("Saved to:")
    print("- data/decision_history.jsonl")
    print("- data/decision_runs.jsonl")


if __name__ == "__main__":
    log_current_decision_snapshot()