def normalize_location_text(value):
    return str(value or "").strip().lower()


def location_has_state(location, state_code):
    location = normalize_location_text(location)
    state_code = normalize_location_text(state_code)

    if not location or not state_code:
        return False

    return (
        location.endswith(f", {state_code}")
        or location.endswith(f" {state_code}")
        or f", {state_code} " in location
    )


def location_state(location):
    location = str(location or "").strip()

    if "," in location:
        parts = location.split(",")
        possible_state = parts[-1].strip().upper()
        if len(possible_state) == 2:
            return possible_state

    words = location.split()
    if words:
        possible_state = words[-1].strip().upper()
        if len(possible_state) == 2:
            return possible_state

    return ""


TARGET_STATE_MAP = {
    "texas": ["TX"],
    "tx": ["TX"],

    "midwest": ["IL", "IN", "OH", "MI", "WI", "MN", "IA", "MO", "KS", "NE", "ND", "SD"],
    "north east": ["PA", "NY", "NJ", "CT", "MA", "RI", "NH", "VT", "ME"],
    "northeast": ["PA", "NY", "NJ", "CT", "MA", "RI", "NH", "VT", "ME"],
    "south east": ["GA", "SC", "NC", "TN", "AL"],
    "southeast": ["GA", "SC", "NC", "TN", "AL"],
    "west": ["CA", "OR", "WA", "NV", "AZ", "UT", "ID"],
}


ROUTE_TOWARD_TARGET_STATES = {
    "texas": ["AL", "MS", "LA", "AR", "OK", "TX"],
    "tx": ["AL", "MS", "LA", "AR", "OK", "TX"],

    "midwest": ["GA", "AL", "TN", "KY", "IN", "IL", "OH", "MO", "WI", "MI", "IA", "MN"],
    "north east": ["GA", "SC", "NC", "VA", "MD", "PA", "NJ", "NY"],
    "northeast": ["GA", "SC", "NC", "VA", "MD", "PA", "NJ", "NY"],
    "west": ["AL", "MS", "LA", "TX", "OK", "NM", "AZ", "CA", "NV", "UT"],
}
