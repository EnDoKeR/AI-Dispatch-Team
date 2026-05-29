from app.market_intelligence.market_baseline import to_number
from app.market_intelligence.market_zone_snapshot import (
    city_from_key,
    city_state_key,
    state_from_key,
)


WATCH_RECOMMENDED_ZONE_STATUSES = [
    "WEAK_EXIT_MARKET",
    "RISKY_EXIT_MARKET",
    "LOW_EXIT_CONFIDENCE",
]


def baseline_value(baseline, key):
    return to_number((baseline or {}).get(key, 0))


def load_rate(load):
    return to_number(getattr(load, "rate", 0))


def load_rpm(load):
    return to_number(getattr(load, "total_rpm", 0))


def is_strong_pay(load, baseline):
    median_rpm = baseline_value(baseline, "median_rpm")
    median_rate = baseline_value(baseline, "median_rate")

    if median_rpm > 0 and load_rpm(load) >= median_rpm + 0.25:
        return True

    if median_rate > 0 and load_rate(load) >= median_rate + 500:
        return True

    return False


def is_high_pay(load, baseline):
    median_rpm = baseline_value(baseline, "median_rpm")
    median_rate = baseline_value(baseline, "median_rate")

    if median_rpm > 0 and load_rpm(load) >= median_rpm:
        return True

    if median_rate > 0 and load_rate(load) >= median_rate:
        return True

    return False


def lookup_zone_context(load, zone_snapshot):
    snapshot = zone_snapshot or {}
    city_key = city_state_key(getattr(load, "delivery", ""))
    state_key = state_from_key(city_key)

    city_context = (snapshot.get("cities") or {}).get(city_key)
    state_context = (snapshot.get("states") or {}).get(state_key)

    return city_key, state_key, city_context, state_context


def default_result(city_key, state_key):
    return {
        "exit_status": "NO_EXIT_CONTEXT",
        "delivery_city": city_from_key(city_key),
        "delivery_state": state_key,
        "city_status": "",
        "state_status": "",
        "clean_exit_count": 0,
        "review_exit_count": 0,
        "rate_check_exit_count": 0,
        "reason": "No current exit market context is available for this delivery market.",
        "recommend_reload_watch": False,
    }


def context_count(context, key):
    return int(to_number((context or {}).get(key, 0)))


def classify_context(load, baseline, active_context):
    zone_status = (active_context or {}).get("status", "")
    clean_count = context_count(active_context, "clean_exit_count")
    review_count = context_count(active_context, "review_exit_count")
    rate_check_count = context_count(active_context, "rate_check_exit_count")
    strong_pay = is_strong_pay(load, baseline)
    high_pay = is_high_pay(load, baseline)

    if zone_status == "LOW_EXIT_CONFIDENCE":
        return (
            "LOW_EXIT_CONFIDENCE",
            bool(strong_pay or high_pay),
            "Exit market has limited data; treat this as low confidence, not a hard bad-zone signal.",
        )

    if clean_count > 0:
        return (
            "CLEAN_EXIT_AVAILABLE",
            False,
            "Current snapshot shows clean exit options in this delivery market.",
        )

    if rate_check_count > 0:
        return (
            "RATE_CHECK_EXITS_AVAILABLE",
            False,
            "No clean exits are visible, but rate-check exit options exist.",
        )

    if zone_status in ["WEAK_EXIT_MARKET", "RISKY_EXIT_MARKET"] and strong_pay:
        return (
            "STRONG_PAY_RELOAD_WATCH_RECOMMENDED",
            True,
            "Inbound load pays above current market context, but the exit market needs monitoring.",
        )

    if zone_status in ["WEAK_EXIT_MARKET", "RISKY_EXIT_MARKET"] and high_pay:
        return (
            "HIGH_PAY_EXIT_PLAN_NEEDED",
            True,
            "Inbound load is not weak, but the exit market needs a plan before booking.",
        )

    if zone_status in WATCH_RECOMMENDED_ZONE_STATUSES:
        return (
            zone_status,
            False,
            "Exit market context is weak or uncertain; keep this as review context only.",
        )

    return (
        zone_status or "NO_EXIT_CONTEXT",
        False,
        "Exit market context is available for review.",
    )


def classify_load_exit_market(load, baseline, zone_snapshot):
    city_key, state_key, city_context, state_context = lookup_zone_context(
        load,
        zone_snapshot,
    )
    active_context = city_context or state_context

    result = default_result(city_key, state_key)

    if not active_context:
        return result

    exit_status, recommend_reload_watch, reason = classify_context(
        load,
        baseline,
        active_context,
    )

    result.update(
        {
            "exit_status": exit_status,
            "city_status": (city_context or {}).get("status", ""),
            "state_status": (state_context or {}).get("status", ""),
            "clean_exit_count": context_count(active_context, "clean_exit_count"),
            "review_exit_count": context_count(active_context, "review_exit_count"),
            "rate_check_exit_count": context_count(
                active_context,
                "rate_check_exit_count",
            ),
            "reason": reason,
            "recommend_reload_watch": recommend_reload_watch,
        }
    )

    return result
