from app.market_intelligence.market_location_helpers import location_state


NEARBY_STATES = {
    "CA": ["NV", "OR", "AZ"],
    "OR": ["CA", "WA", "ID", "NV"],
    "WA": ["OR", "ID"],
    "NV": ["CA", "OR", "ID", "UT", "AZ"],
    "AZ": ["CA", "NV", "UT", "NM"],
    "TX": ["OK", "AR", "LA", "NM"],
    "FL": ["GA", "AL"],
    "GA": ["FL", "AL", "TN", "SC", "NC"],
    "AL": ["FL", "GA", "MS", "TN"],
    "TN": ["AL", "GA", "KY", "AR", "MS", "MO", "NC"],
    "CO": ["WY", "NE", "KS", "OK", "NM", "AZ", "UT"],
    "IL": ["WI", "IA", "MO", "KY", "IN"],
    "IN": ["IL", "MI", "OH", "KY"],
    "OH": ["IN", "MI", "PA", "WV", "KY"],
}


def pickup_region_conflict_with_driver(load, search_request):
    driver_location = str(getattr(search_request, "current_location", "") or "").strip()
    pickup_location = str(load.pickup or load.origin or "").strip()

    if not driver_location or not pickup_location:
        return False

    driver_state = location_state(driver_location)
    pickup_state = location_state(pickup_location)

    if not driver_state or not pickup_state:
        return False

    if driver_state == pickup_state:
        return False

    allowed_neighbor_states = NEARBY_STATES.get(driver_state, [])

    if pickup_state in allowed_neighbor_states:
        return False

    if load.empty_miles <= 250:
        return True

    return False
