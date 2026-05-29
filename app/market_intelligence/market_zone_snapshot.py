from app.market_intelligence.market_baseline import (
    numeric_average,
    numeric_median,
    to_number,
)
from app.market_intelligence.market_location_helpers import location_state
from app.market_intelligence.telegram_duplicate_keys import load_repost_identity_key


def city_state_key(location):
    text = str(location or "").strip()

    if "," not in text:
        return text

    city = text.split(",")[0].strip()
    state = text.split(",")[-1].strip().split()[0].upper()

    if not city or not state:
        return text

    return f"{city}, {state}"


def city_from_key(key):
    if "," not in key:
        return key

    return key.split(",")[0].strip()


def state_from_key(key):
    state = location_state(key)

    if state:
        return state

    if "," not in key:
        return ""

    return key.split(",")[-1].strip().split()[0].upper()


def load_status(load):
    return str(getattr(load, "driver_match_status", "") or "").upper()


def load_review_category(load):
    review_category = getattr(load, "review_category", "")

    if callable(review_category):
        return str(review_category() or "").upper()

    return str(review_category or getattr(load, "category", "") or "").upper()


def is_rate_check_exit(load):
    if load_review_category(load) == "RATE CHECK":
        return True

    return to_number(getattr(load, "rate", 0)) <= 0


def is_clean_exit(load):
    return load_status(load) == "MATCH"


def is_review_exit(load):
    return load_status(load) == "REVIEW_ONCE" and not is_rate_check_exit(load)


def is_blocked(load):
    return load_status(load) == "BLOCK"


def classify_zone_status(load_count, clean_count, review_count, rate_check_count, median_rpm):
    if load_count < 3:
        return "LOW_EXIT_CONFIDENCE"

    if clean_count >= 2 and median_rpm >= 2.0:
        return "STRONG_EXIT_MARKET"

    if clean_count == 0 and (review_count + rate_check_count) >= 2:
        return "RISKY_EXIT_MARKET"

    return "WEAK_EXIT_MARKET"


def summarize_zone_loads(loads, city="", state=""):
    rpm_values = [getattr(load, "total_rpm", 0) for load in loads]
    rate_values = [getattr(load, "rate", 0) for load in loads]
    median_rpm = numeric_median(rpm_values)

    clean_exit_count = len([
        load for load in loads if is_clean_exit(load)
    ])
    review_exit_count = len([
        load for load in loads if is_review_exit(load)
    ])
    rate_check_exit_count = len([
        load for load in loads if is_rate_check_exit(load)
    ])

    return {
        "city": city,
        "state": state,
        "load_count": len(loads),
        "clean_exit_count": clean_exit_count,
        "review_exit_count": review_exit_count,
        "rate_check_exit_count": rate_check_exit_count,
        "blocked_count": len([
            load for load in loads if is_blocked(load)
        ]),
        "avg_rpm": numeric_average(rpm_values),
        "median_rpm": median_rpm,
        "avg_rate": numeric_average(rate_values),
        "median_rate": numeric_median(rate_values),
        "best_rpm": max([to_number(value) for value in rpm_values], default=0),
        "best_rate": max([to_number(value) for value in rate_values], default=0),
        "status": classify_zone_status(
            len(loads),
            clean_exit_count,
            review_exit_count,
            rate_check_exit_count,
            median_rpm,
        ),
    }


def dedupe_loads(loads):
    deduped_loads = []
    seen_keys = set()

    for load in loads:
        key = load_repost_identity_key(load)

        if key in seen_keys:
            continue

        seen_keys.add(key)
        deduped_loads.append(load)

    return deduped_loads


def group_by_city(loads):
    grouped = {}

    for load in loads:
        key = city_state_key(getattr(load, "delivery", ""))
        grouped.setdefault(key, []).append(load)

    return grouped


def group_by_state(loads):
    grouped = {}

    for load in loads:
        state = location_state(getattr(load, "delivery", ""))
        grouped.setdefault(state, []).append(load)

    return grouped


def build_market_zone_snapshot(loads):
    source_loads = list(loads)
    deduped_loads = dedupe_loads(source_loads)

    cities = {}
    for key, city_loads in group_by_city(deduped_loads).items():
        cities[key] = summarize_zone_loads(
            city_loads,
            city=city_from_key(key),
            state=state_from_key(key),
        )

    states = {}
    for state, state_loads in group_by_state(deduped_loads).items():
        states[state] = summarize_zone_loads(
            state_loads,
            city="",
            state=state,
        )

    return {
        "source_load_count": len(source_loads),
        "load_count": len(deduped_loads),
        "cities": cities,
        "states": states,
    }
