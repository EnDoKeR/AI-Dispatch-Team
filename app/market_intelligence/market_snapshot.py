from pathlib import Path
from app.market_intelligence.reload_chain import build_chain_candidates
from app.market_intelligence.load_source import load_market_loads
from app.market_intelligence.search_request import load_search_request
from app.market_intelligence.decision_logger import log_decisions
from app.market_intelligence.driver_profile_loader import apply_driver_profile_to_search_request
from app.market_intelligence.telegram_notifier import (
    send_chain_candidates_to_telegram,
    send_market_summary_to_telegram,
    send_review_once_to_telegram,
    send_search_health_check_to_telegram,
    send_top_opportunities_to_telegram,
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


def apply_search_request(loads, search_request):
    for load in loads:
        load.apply_search_request(search_request)

    return loads


def average_score(loads):
    if not loads:
        return 0

    return round(
        sum(load.opportunity_score() for load in loads)
        / len(loads)
    )


def bucket_stats(loads):
    buckets = {
        "0-450": [],
        "450-700": [],
        "700-1300": [],
        "1300+": [],
    }

    for load in loads:
        buckets[load.bucket].append(load)

    result = {}

    for bucket_name, bucket_loads in buckets.items():
        qualified = [
            load
            for load in bucket_loads
            if load.is_qualified()
        ]

        good = [
            load
            for load in bucket_loads
            if load.is_good()
        ]

        clean_match = [
            load
            for load in bucket_loads
            if load.is_good()
            and load.driver_match_status == "MATCH"
        ]

        review_once = [
            load
            for load in bucket_loads
            if load.is_good()
            and load.driver_match_status == "REVIEW_ONCE"
        ]

        blocked = [
            load
            for load in bucket_loads
            if load.driver_match_status == "BLOCK"
        ]

        if bucket_loads:
            avg_rpm = round(
                sum(load.total_rpm for load in bucket_loads)
                / len(bucket_loads),
                2,
            )

            avg_rate = round(
                sum(load.rate for load in bucket_loads)
                / len(bucket_loads),
            )

        else:
            avg_rpm = 0
            avg_rate = 0

        result[bucket_name] = {
            "total_loads": len(bucket_loads),
            "qualified_loads": len(qualified),
            "good_loads": len(good),
            "clean_match_loads": len(clean_match),
            "review_once_loads": len(review_once),
            "blocked_loads": len(blocked),
            "avg_total_rpm": avg_rpm,
            "avg_rate": avg_rate,
            "avg_opportunity_score": average_score(bucket_loads),
            "avg_qualified_score": average_score(qualified),
            "avg_good_score": average_score(good),
            "avg_clean_match_score": average_score(clean_match),
            "avg_review_once_score": average_score(review_once),
        }

    return result


def fit_stats(loads):
    clean_matches = [
        load
        for load in loads
        if load.is_good()
        and load.driver_match_status == "MATCH"
    ]

    review_once = [
        load
        for load in loads
        if load.is_good()
        and load.driver_match_status == "REVIEW_ONCE"
    ]

    blocked = [
        load
        for load in loads
        if load.driver_match_status == "BLOCK"
    ]

    qualified = [
        load
        for load in loads
        if load.is_qualified()
    ]

    good = [
        load
        for load in loads
        if load.is_good()
    ]

    if len(clean_matches) >= 3:
        driver_fit = "GOOD"
    elif len(clean_matches) >= 1:
        driver_fit = "WORKABLE"
    elif len(review_once) >= 3:
        driver_fit = "REVIEW_ONLY"
    elif len(review_once) >= 1:
        driver_fit = "WEAK_FIT"
    else:
        driver_fit = "NO_MATCH"

    return {
        "driver_fit": driver_fit,
        "clean_matches": len(clean_matches),
        "review_once": len(review_once),
        "blocked": len(blocked),
        "qualified": len(qualified),
        "good": len(good),
    }


def choose_best_bucket(stats):
    best_bucket = None
    best_score = -1

    for bucket, data in stats.items():
        score = (
            data["clean_match_loads"] * 5
            + data["good_loads"] * 3
            + data["qualified_loads"] * 2
            + data["avg_clean_match_score"] / 8
            + data["avg_good_score"] / 15
        )

        if score > best_score:
            best_score = score
            best_bucket = bucket

    return best_bucket


def market_recommendation(stats, fit):
    total_good = sum(
        data["good_loads"]
        for data in stats.values()
    )

    total_qualified = sum(
        data["qualified_loads"]
        for data in stats.values()
    )

    total_clean_matches = fit["clean_matches"]
    total_review_once = fit["review_once"]
    total_blocked = fit["blocked"]

    best_bucket = choose_best_bucket(stats)

    if total_good >= 6:
        market_activity = "GOOD"
    elif total_good >= 3:
        market_activity = "MEDIUM"
    elif total_qualified >= 2:
        market_activity = "WEAK"
    else:
        market_activity = "BAD"

    driver_fit = fit["driver_fit"]

    if driver_fit == "GOOD":
        action_status = "STRONG_MATCHES_AVAILABLE"
    elif driver_fit == "WORKABLE":
        action_status = "SOME_MATCHES_AVAILABLE"
    elif driver_fit == "REVIEW_ONLY":
        action_status = "REVIEW_ONLY"
    elif driver_fit == "WEAK_FIT":
        action_status = "WEAK_FIT"
    else:
        action_status = "NO_CLEAN_MATCHES"

    return {
        "market_activity": market_activity,
        "driver_fit": driver_fit,
        "action_status": action_status,
        "best_bucket": best_bucket,
        "total_good_loads": total_good,
        "total_qualified_loads": total_qualified,
        "total_clean_matches": total_clean_matches,
        "total_review_once": total_review_once,
        "total_blocked": total_blocked,

        # backwards compatibility for old telegram_notifier code
        "market_status": market_activity,
    }


def build_market_explanation(stats, recommendation):
    best_bucket = recommendation["best_bucket"]
    best_data = stats[best_bucket]

    explanation = []

    explanation.append(
        f"Market activity is {recommendation['market_activity']} based on all current available loads."
    )

    explanation.append(
        f"Driver fit is {recommendation['driver_fit']} based on clean matches and review-once options."
    )

    explanation.append(
        f"Best distance bucket is {best_bucket} miles."
    )

    explanation.append(
        f"This bucket has {best_data['total_loads']} total loads, "
        f"{best_data['qualified_loads']} qualified loads, "
        f"{best_data['good_loads']} good loads, "
        f"{best_data['clean_match_loads']} clean matches, "
        f"and {best_data['review_once_loads']} review-once options."
    )

    explanation.append(
        f"Average total RPM in this bucket is ${best_data['avg_total_rpm']}."
    )

    explanation.append(
        f"Average gross in this bucket is ${best_data['avg_rate']}."
    )

    explanation.append(
        f"Average score for clean matches is {best_data['avg_clean_match_score']}."
    )

    explanation.append(
        f"Average score for review-once loads is {best_data['avg_review_once_score']}."
    )

    return explanation


def get_top_opportunities(loads, limit=5):
    good_loads = [
        load
        for load in loads
        if load.is_good()
        and load.driver_match_status == "MATCH"
    ]

    sorted_loads = sorted(
        good_loads,
        key=lambda load: (
            load.opportunity_score(),
            load.rate,
            load.total_rpm,
            -load.empty_miles,
        ),
        reverse=True,
    )

    return sorted_loads[:limit]


def get_review_once_loads(loads, limit=5):
    review_loads = []

    for load in loads:
        if load.driver_match_status != "REVIEW_ONCE":
            continue

        is_rate_check = False

        for reason in getattr(load, "driver_match_notes", []):
            reason_text = str(reason or "").lower()

            if (
                "rate is missing" in reason_text
                or "posted as $0" in reason_text
                or "rate check" in reason_text
                or "check rate with broker" in reason_text
            ):
                is_rate_check = True
                break

        if load.is_good() or is_rate_check:
            review_loads.append(load)

    sorted_loads = sorted(
        review_loads,
        key=lambda load: (
            1 if any(
                "rate is missing" in str(reason or "").lower()
                or "posted as $0" in str(reason or "").lower()
                or "rate check" in str(reason or "").lower()
                for reason in getattr(load, "driver_match_notes", [])
            ) else 0,
            load.opportunity_score(),
            load.rate,
            load.total_rpm,
            -load.empty_miles,
        ),
        reverse=True,
    )

    return sorted_loads[:limit]


def print_driver_report(
    request_file,
    stats,
    recommendation,
    top_opportunities,
    review_once_loads,
    search_request,
    chain_candidates
    ):
    print("\nReload Chain Candidates:")
    if not chain_candidates:
        print("No reload chain candidates.")

    for index, candidate in enumerate(chain_candidates, start=1):
        first_load = candidate["first_load"]
        reload_load = candidate["reload_load"]
        chain_data = candidate["chain_data"]

        print(
            f"{index}. {first_load.pickup} -> {first_load.delivery} "
            f"+ {reload_load.pickup} -> {reload_load.delivery} | "
            f"Gross ${chain_data['total_gross']} | "
            f"RPM ${chain_data['total_rpm']} | "
            f"Score {chain_data['chain_score']}"
        )
    print("\n" + "=" * 60)
    print(f"ACTIVE SEARCH: {request_file}")
    print("=" * 60)

    print(f"Driver: {search_request.driver_name}")
    print(f"Location: {search_request.current_location}")
    print(f"Available: {search_request.available_time}")
    print(f"Equipment: {search_request.equipment}")
    print(f"Driver Max Weight: {search_request.max_weight}")
    print(f"Default Max Empty: {search_request.max_empty_miles}")
    print(f"Target Direction: {search_request.target_direction}")

    print("\nMarket:")
    print(f"Market Activity: {recommendation['market_activity']}")
    print(f"Driver Fit: {recommendation['driver_fit']}")
    print(f"Action Status: {recommendation['action_status']}")
    print(f"Best Bucket: {recommendation['best_bucket']}")
    print(f"Good Loads: {recommendation['total_good_loads']}")
    print(f"Qualified Loads: {recommendation['total_qualified_loads']}")
    print(f"Clean Matches: {recommendation['total_clean_matches']}")
    print(f"Review Once: {recommendation['total_review_once']}")
    print(f"Blocked: {recommendation['total_blocked']}")

    print("\nTop Match Opportunities:")
    if not top_opportunities:
        print("No clean match opportunities.")

    for index, load in enumerate(top_opportunities, start=1):
        print(
            f"{index}. {load.pickup} -> {load.delivery} | "
            f"${load.rate} | RPM ${load.total_rpm} | "
            f"Score {load.opportunity_score()} | {load.suggested_action()}"
        )

    print("\nReview Once Opportunities:")
    if not review_once_loads:
        print("No review-once opportunities.")

    for index, load in enumerate(review_once_loads, start=1):
        print(
            f"{index}. {load.pickup} -> {load.delivery} | "
            f"${load.rate} | RPM ${load.total_rpm} | "
            f"Score {load.opportunity_score()} | Notes: {load.driver_match_notes}"
        )

def prepare_route_fallback(loads, search_request):
    mode = getattr(search_request, "target_direction_mode", "SOFT")

    if mode != "TARGET_THEN_ROUTE":
        search_request.route_fallback_active = False
        return search_request

    direct_target_loads = []

    for load in loads:
        if load.matches_target_city_radius(search_request):
            direct_target_loads.append(load)
            continue

        if load.matches_target_state_or_region(search_request):
            direct_target_loads.append(load)

    if direct_target_loads:
        search_request.route_fallback_active = False
        print(
            f"Direct target loads found for {search_request.driver_name}: "
            f"{len(direct_target_loads)}. Route fallback disabled."
        )
    else:
        search_request.route_fallback_active = True
        print(
            f"No direct target loads found for {search_request.driver_name}. "
            f"Route fallback enabled."
        )

    return search_request

def process_search_request(request_file):
    search_request = load_search_request(request_file)
    search_request = apply_driver_profile_to_search_request(search_request)

    search_location = search_request.current_location

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

    explanation = build_market_explanation(
        stats,
        recommendation,
    )

    top_opportunities = get_top_opportunities(loads)
    review_once_loads = get_review_once_loads(loads)

    chain_candidates = build_chain_candidates(
        loads,
        search_request,
        limit=5,
    )

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

    telegram_loads = top_opportunities

    print(f"\n===== TELEGRAM SUMMARY SEND вЂ” {search_request.driver_name} =====\n")

    send_market_summary_to_telegram(
        stats,
        recommendation,
        top_opportunities,
        search_request,
        search_location=search_location,
    )

    print(f"\n===== TELEGRAM MATCH LOADS SEND вЂ” {search_request.driver_name} =====\n")

    send_top_opportunities_to_telegram(
        telegram_loads,
        search_request,
        limit=3,
    )

    print(f"\n===== TELEGRAM REVIEW ONCE SEND вЂ” {search_request.driver_name} =====\n")

    send_review_once_to_telegram(
        review_once_loads,
        search_request,
        limit=3,
    )

    print(f"\n===== TELEGRAM SEARCH HEALTH CHECK вЂ” {search_request.driver_name} =====\n")

    send_search_health_check_to_telegram(
        search_request,
        loads,
        top_opportunities,
        review_once_loads,
        monitored_minutes=30,
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
