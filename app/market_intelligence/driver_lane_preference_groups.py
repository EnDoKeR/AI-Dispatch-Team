GROUP_SUM_FIELDS = [
    "booked_cases",
    "ratecon_received_cases",
    "sent_to_driver_cases",
    "rejected_cases",
    "skipped_cases",
    "covered_cases",
    "final_booked",
    "final_ratecon_received",
    "final_rejected",
    "final_skipped",
    "final_covered",
    "match_cases",
    "review_once_cases",
    "blocked_cases",
    "load_opportunity_cases",
    "rate_check_cases",
    "broker_review_cases",
]


def get_row_value(row, field_name, default=None):
    try:
        value = row[field_name]
    except Exception:
        value = default

    if value is None:
        return default

    return value


def build_empty_lane_group(driver_name, pickup, delivery):
    return {
        "driver_name": driver_name,
        "pickup": pickup,
        "delivery": delivery,
        "feedback_counts": {},
        "case_count": 0,
        "avg_rate_values": [],
        "avg_miles_values": [],
        "avg_rpm_values": [],
        "avg_weight_values": [],
        "booked_cases": 0,
        "ratecon_received_cases": 0,
        "sent_to_driver_cases": 0,
        "rejected_cases": 0,
        "skipped_cases": 0,
        "covered_cases": 0,
        "final_booked": 0,
        "final_ratecon_received": 0,
        "final_rejected": 0,
        "final_skipped": 0,
        "final_covered": 0,
        "match_cases": 0,
        "review_once_cases": 0,
        "blocked_cases": 0,
        "load_opportunity_cases": 0,
        "rate_check_cases": 0,
        "broker_review_cases": 0,
        "latest_feedback": "",
    }


def build_lane_groups(rows):
    lane_groups = {}

    for row in rows:
        key = (
            get_row_value(row, "driver_name", "UNKNOWN") or "UNKNOWN",
            get_row_value(row, "pickup", "UNKNOWN") or "UNKNOWN",
            get_row_value(row, "delivery", "UNKNOWN") or "UNKNOWN",
        )

        if key not in lane_groups:
            lane_groups[key] = build_empty_lane_group(
                driver_name=key[0],
                pickup=key[1],
                delivery=key[2],
            )

        group = lane_groups[key]
        feedback = get_row_value(row, "feedback", "UNKNOWN") or "UNKNOWN"

        group["feedback_counts"][feedback] = (
            group["feedback_counts"].get(feedback, 0)
            + (get_row_value(row, "feedback_count", 0) or 0)
        )

        group["case_count"] += get_row_value(row, "case_count", 0) or 0

        if get_row_value(row, "avg_rate") is not None:
            group["avg_rate_values"].append(get_row_value(row, "avg_rate"))

        if get_row_value(row, "avg_total_miles") is not None:
            group["avg_miles_values"].append(get_row_value(row, "avg_total_miles"))

        if get_row_value(row, "avg_total_rpm") is not None:
            group["avg_rpm_values"].append(get_row_value(row, "avg_total_rpm"))

        if get_row_value(row, "avg_weight") is not None:
            group["avg_weight_values"].append(get_row_value(row, "avg_weight"))

        for field_name in GROUP_SUM_FIELDS:
            group[field_name] += get_row_value(row, field_name, 0) or 0

        latest_feedback = get_row_value(row, "latest_feedback", "") or ""

        if latest_feedback > group["latest_feedback"]:
            group["latest_feedback"] = latest_feedback

    return list(lane_groups.values())
