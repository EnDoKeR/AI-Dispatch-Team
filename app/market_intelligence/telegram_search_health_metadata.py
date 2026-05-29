def safe_attr(source, field_name, default=""):
    if source is None:
        return default

    value = getattr(source, field_name, default)

    if value is None:
        return default

    return value


def first_non_empty(*values):
    for value in values:
        if value is None:
            continue

        if str(value).strip():
            return value

    return ""


def safe_count(values):
    if values is None:
        return 0

    try:
        return len(values)
    except TypeError:
        return 0


def count_value(value, default=0):
    if value is None:
        return default

    if value == "":
        return default

    return value


def build_search_health_metadata(
    search_request=None,
    loads=None,
    top_opportunities=None,
    review_once_loads=None,
    monitored_minutes=30,
    qualified_loads=0,
    clean_matches=None,
    blocked_count=0,
    health_status="",
    action_status="",
    reason="",
):
    return {
        "message_type": "SEARCH_HEALTH_CHECK",
        "category": "SEARCH HEALTH CHECK",
        "driver_name": safe_attr(search_request, "driver_name", ""),
        "pickup": "",
        "delivery": "",
        "rate": "",
        "broker": "",
        "broker_mc": "",
        "reference_id": "",
        "search_area": first_non_empty(
            safe_attr(search_request, "current_location", ""),
            safe_attr(search_request, "search_area", ""),
        ),
        "current_location": safe_attr(search_request, "current_location", ""),
        "available_time": safe_attr(search_request, "available_time", ""),
        "equipment": safe_attr(search_request, "equipment", ""),
        "target_direction": safe_attr(search_request, "target_direction", ""),
        "monitored_minutes": count_value(monitored_minutes, default=30),
        "total_loads": safe_count(loads),
        "qualified_loads": count_value(qualified_loads),
        "clean_matches": count_value(
            clean_matches,
            default=safe_count(top_opportunities),
        ),
        "top_opportunities": safe_count(top_opportunities),
        "review_once_count": safe_count(review_once_loads),
        "blocked_count": count_value(blocked_count),
        "health_status": health_status or "",
        "action_status": action_status or "",
        "reason": reason or "",
    }
