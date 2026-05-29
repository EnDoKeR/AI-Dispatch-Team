from app.market_intelligence.market_baseline import to_number
from app.market_intelligence.market_location_helpers import location_state
from app.market_intelligence.market_zone_snapshot import city_state_key


SECONDARY_RISK_STATUSES = [
    "WEAK_EXIT_MARKET",
    "RISKY_EXIT_MARKET",
    "LOW_EXIT_CONFIDENCE",
]


def market_median_rpm(market_baseline):
    return to_number((market_baseline or {}).get("median_rpm", 0))


def load_rate(load):
    return to_number(getattr(load, "rate", 0))


def loaded_miles(load):
    return to_number(getattr(load, "loaded_miles", 0))


def known_empty_between_loads(inbound_load, exit_load):
    distance_func = getattr(inbound_load, "distance_between_known_cities", None)

    if not callable(distance_func):
        return 0, False

    inbound_delivery = city_state_key(getattr(inbound_load, "delivery", ""))
    exit_pickup = city_state_key(getattr(exit_load, "pickup", ""))
    distance = distance_func(inbound_delivery, exit_pickup)

    if distance is None:
        return 0, False

    return to_number(distance), True


def base_result(inbound_load, exit_load, market_baseline, zone_snapshot):
    inbound_rate = load_rate(inbound_load)
    exit_rate = load_rate(exit_load)
    inbound_miles = loaded_miles(inbound_load)
    exit_miles = loaded_miles(exit_load)
    empty_between, empty_between_known = known_empty_between_loads(
        inbound_load,
        exit_load,
    )
    combined_gross = inbound_rate + exit_rate
    combined_miles = inbound_miles + exit_miles + empty_between

    if combined_miles > 0:
        combined_rpm = round(combined_gross / combined_miles, 2)
    else:
        combined_rpm = 0

    secondary_exit_status = lookup_secondary_exit_status(
        exit_load,
        zone_snapshot,
    )
    context_labels = []

    if secondary_exit_status in SECONDARY_RISK_STATUSES:
        context_labels.append("SECONDARY_EXIT_RISK")

    return {
        "leg_count": 2,
        "chain_status": "",
        "context_labels": context_labels,
        "inbound_rate": inbound_rate,
        "exit_rate": exit_rate,
        "combined_gross": combined_gross,
        "inbound_loaded_miles": inbound_miles,
        "exit_loaded_miles": exit_miles,
        "empty_between_loads": empty_between,
        "empty_between_loads_known": empty_between_known,
        "combined_miles": combined_miles,
        "combined_rpm": combined_rpm,
        "market_median_rpm": market_median_rpm(market_baseline),
        "rpm_vs_market": round(
            combined_rpm - market_median_rpm(market_baseline),
            2,
        ),
        "secondary_exit_status": secondary_exit_status,
        "gross_per_day_warning": "",
        "estimated_days_known": False,
        "reason": "",
    }


def lookup_secondary_exit_status(exit_load, zone_snapshot):
    snapshot = zone_snapshot or {}
    city_key = city_state_key(getattr(exit_load, "delivery", ""))
    state_key = location_state(city_key)
    cities = snapshot.get("cities") or {}
    states = snapshot.get("states") or {}
    context = cities.get(city_key) or states.get(state_key) or {}

    return context.get("status", "")


def has_incomplete_chain_data(result):
    return (
        result["inbound_rate"] <= 0
        or result["inbound_loaded_miles"] <= 0
        or result["exit_loaded_miles"] <= 0
        or result["market_median_rpm"] <= 0
    )


def classify_chain(result):
    if result["exit_rate"] <= 0:
        return (
            "RATE_CHECK_CHAIN",
            "Exit load has no confirmed rate; treat this chain as rate-check context only.",
        )

    if has_incomplete_chain_data(result):
        return (
            "INCOMPLETE_CHAIN_DATA",
            "Chain is missing rate, mileage, or market median context.",
        )

    rpm_vs_market = result["rpm_vs_market"]

    if rpm_vs_market >= 0.50:
        return (
            "STRONG_CHAIN",
            "Combined RPM is at least $0.50 above current market median.",
        )

    if rpm_vs_market >= 0.25:
        return (
            "WORKABLE_CHAIN",
            "Combined RPM is at least $0.25 above current market median.",
        )

    if rpm_vs_market >= -0.05:
        return (
            "WORKABLE_CHAIN",
            "Combined RPM is around current market median.",
        )

    return (
        "WEAK_CHAIN",
        "Combined RPM is below current market median.",
    )


def score_two_load_chain(
    inbound_load,
    exit_load,
    market_baseline=None,
    zone_snapshot=None,
):
    result = base_result(
        inbound_load,
        exit_load,
        market_baseline,
        zone_snapshot,
    )
    chain_status, reason = classify_chain(result)

    result["chain_status"] = chain_status
    result["reason"] = reason

    if chain_status not in result["context_labels"]:
        result["context_labels"].append(chain_status)

    return result
