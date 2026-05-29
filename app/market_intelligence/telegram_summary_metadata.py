def safe_attr(source, field_name, default=""):
    if source is None:
        return default

    value = getattr(source, field_name, default)

    if value is None:
        return default

    return value


def safe_mapping_value(source, field_name, default=""):
    if not isinstance(source, dict):
        return default

    value = source.get(field_name, default)

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


def count_value(*values):
    for value in values:
        if value is None:
            continue

        if value == "":
            continue

        return value

    return 0


def build_market_summary_metadata(
    stats=None,
    recommendation=None,
    top_opportunities=None,
    search_request=None,
):
    stats = stats if isinstance(stats, dict) else {}
    recommendation = recommendation if isinstance(recommendation, dict) else {}

    return {
        "message_type": "MARKET_SNAPSHOT",
        "category": "MARKET SNAPSHOT",
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
        "market_activity": first_non_empty(
            safe_mapping_value(recommendation, "market_activity", ""),
            safe_mapping_value(recommendation, "market_status", ""),
            safe_mapping_value(stats, "market_activity", ""),
            safe_mapping_value(stats, "market_status", ""),
        ),
        "driver_fit": safe_mapping_value(recommendation, "driver_fit", ""),
        "action_status": safe_mapping_value(recommendation, "action_status", ""),
        "best_bucket": safe_mapping_value(recommendation, "best_bucket", ""),
        "good_loads": count_value(
            safe_mapping_value(recommendation, "total_good_loads", None),
            safe_mapping_value(recommendation, "good_loads", None),
            safe_mapping_value(stats, "good_loads", None),
        ),
        "qualified_loads": count_value(
            safe_mapping_value(recommendation, "total_qualified_loads", None),
            safe_mapping_value(recommendation, "qualified_loads", None),
            safe_mapping_value(stats, "qualified_loads", None),
        ),
        "clean_match_count": count_value(
            safe_mapping_value(recommendation, "total_clean_matches", None),
            safe_mapping_value(recommendation, "clean_match_count", None),
            safe_mapping_value(stats, "clean_match_count", None),
            safe_mapping_value(stats, "clean_match_loads", None),
        ),
        "review_once_count": count_value(
            safe_mapping_value(recommendation, "total_review_once", None),
            safe_mapping_value(recommendation, "review_once_count", None),
            safe_mapping_value(stats, "review_once_count", None),
            safe_mapping_value(stats, "review_once_loads", None),
        ),
        "blocked_count": count_value(
            safe_mapping_value(recommendation, "total_blocked", None),
            safe_mapping_value(recommendation, "blocked_count", None),
            safe_mapping_value(stats, "blocked_count", None),
            safe_mapping_value(stats, "blocked_loads", None),
        ),
    }
