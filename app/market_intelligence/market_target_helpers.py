from app.market_intelligence.market_location_helpers import (
    ROUTE_TOWARD_TARGET_STATES,
    TARGET_STATE_MAP,
    location_state,
)


def matches_target_city_radius(load, search_request):
    target_city = getattr(search_request, "target_city", "") or ""
    target_city = str(target_city).strip().lower()

    if not target_city:
        return False

    destination = str(load.destination or load.delivery or "").strip().lower()

    if not destination:
        return False

    return target_city in destination


def target_states(search_request):
    target = str(getattr(search_request, "target_direction", "") or "").strip().lower()
    return TARGET_STATE_MAP.get(target, [])


def route_toward_target_states(search_request):
    target = str(getattr(search_request, "target_direction", "") or "").strip().lower()
    return ROUTE_TOWARD_TARGET_STATES.get(target, [])


def delivery_matches_target(load, search_request):
    delivery_state = location_state(load.delivery)

    if not delivery_state:
        return False

    if delivery_state in target_states(search_request):
        return True

    return False


def delivery_is_along_route(load, search_request):
    delivery_state = location_state(load.delivery)

    if not delivery_state:
        return False

    if delivery_state in target_states(search_request):
        return True

    if delivery_state in route_toward_target_states(search_request):
        return True

    return False


def is_strong_off_target_exception(load):
    return (
        load.total_rpm >= 4.5
        and load.rate >= 2800
        and load.empty_miles <= 150
        and load.loaded_miles >= 450
    )


def should_block_off_target(load, search_request):
    if delivery_matches_target(load, search_request):
        return False

    if delivery_is_along_route(load, search_request):
        return False

    if is_strong_off_target_exception(load):
        return False

    return True


def off_target_review_reason(load, search_request):
    if delivery_matches_target(load, search_request):
        return ""

    if delivery_is_along_route(load, search_request):
        return f"Load is along route toward {search_request.target_direction}."

    if is_strong_off_target_exception(load):
        return (
            f"Strong off-target exception: RPM ${load.total_rpm} "
            f"and gross ${load.rate}, but delivery does not match target direction."
        )

    return f"Delivery does not match target direction: {search_request.target_direction}."


def matches_target_state_or_region(load, search_request):
    target = getattr(search_request, "target_direction", "") or ""
    target = str(target).strip().lower()

    if not target:
        return False

    destination = str(load.destination or load.delivery or "").strip().lower()

    if not destination:
        return False

    state_regions = {
        "midwest": [
            "il", "in", "oh", "mi", "wi", "mn", "ia", "mo", "ks", "ne", "sd", "nd"
        ],
        "texas": ["tx"],
        "south": [
            "tx", "ok", "ar", "la", "ms", "al", "ga", "fl", "sc", "nc", "tn", "ky"
        ],
        "southeast": [
            "fl", "ga", "sc", "nc", "tn", "al", "ms"
        ],
        "northeast": [
            "pa", "ny", "nj", "ct", "ma", "ri", "me", "nh", "vt", "md", "de"
        ],
        "west": [
            "ca", "or", "wa", "nv", "az", "ut", "id", "mt", "wy", "co", "nm"
        ],
        "pacific northwest": ["wa", "or", "id"],
        "pnw": ["wa", "or", "id"],
        "mountain": ["co", "ut", "id", "mt", "wy", "nv", "az", "nm"],
    }

    state_aliases = {
        "texas": "tx",
        "california": "ca",
        "florida": "fl",
        "illinois": "il",
        "indiana": "in",
        "ohio": "oh",
        "michigan": "mi",
        "wisconsin": "wi",
        "minnesota": "mn",
        "iowa": "ia",
        "missouri": "mo",
        "georgia": "ga",
        "north carolina": "nc",
        "south carolina": "sc",
        "tennessee": "tn",
        "kentucky": "ky",
        "pennsylvania": "pa",
        "new york": "ny",
        "new jersey": "nj",
        "washington": "wa",
        "oregon": "or",
        "arizona": "az",
        "colorado": "co",
        "utah": "ut",
    }

    if target in destination:
        return True

    target_state = state_aliases.get(target, target)

    if destination.endswith(f", {target_state}") or destination.endswith(f" {target_state}"):
        return True

    if target in state_regions:
        for state_code in state_regions[target]:
            if destination.endswith(f", {state_code}") or destination.endswith(f" {state_code}"):
                return True

    return False


def is_along_route_toward_target(load, search_request):
    route_fallback_active = getattr(search_request, "route_fallback_active", False)

    if not route_fallback_active:
        return False

    target = str(getattr(search_request, "target_direction", "") or "").lower()
    destination = str(load.destination or load.delivery or "").lower()

    along_route_map = {
        "texas": ["ga", "al", "ms", "la", "tx", "ok", "ar"],
        "midwest": ["ga", "tn", "ky", "oh", "in", "il", "mo", "wi", "mi"],
        "northeast": ["ga", "sc", "nc", "va", "md", "pa", "nj", "ny"],
        "west": ["al", "ms", "la", "tx", "ok", "nm", "az", "co", "ut"],
    }

    states = along_route_map.get(target, [])

    for state_code in states:
        if destination.endswith(f", {state_code}") or destination.endswith(f" {state_code}"):
            return True

    return False
