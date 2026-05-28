def safe_value(value, fallback="NEEDS CHECK"):
    if value is None:
        return fallback

    value = str(value).strip()

    if not value:
        return fallback

    return value


def extract_state(location):
    text = str(location).strip().upper()

    if "," in text:
        parts = text.split(",")
        state_part = parts[-1].strip()

        if state_part:
            return state_part.split()[0]

    words = text.split()

    if words:
        return words[-1]

    return ""


def delivery_zone_outlook(destination):
    state = extract_state(destination)

    strong_states = [
        "IL",
        "IN",
        "OH",
        "PA",
        "GA",
        "NC",
        "SC",
        "TX",
    ]

    workable_states = [
        "TN",
        "KY",
        "MO",
        "AR",
        "AL",
        "FL",
        "VA",
    ]

    risky_states = [
        "MT",
        "ND",
        "SD",
        "WY",
        "ID",
        "NM",
        "ME",
    ]

    if state in strong_states:
        return "GOOD / STRONG RELOAD AREA"

    if state in workable_states:
        return "WORKABLE / CHECK RELOADS"

    if state in risky_states:
        return "RISKY / EXIT PLAN NEEDED"

    return "UNKNOWN / NEEDS MARKET CHECK"
