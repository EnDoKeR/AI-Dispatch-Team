from pathlib import Path

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


from app.market_intelligence.driver_lane_preference_core import (
    average,
    classify_lane_signal,
    format_driver_lane_preference_status,
    format_lane_preference_status,
    get_sample_quality,
    is_valid_driver_name,
    lane_sample_size,
    normalize_location,
    normalize_text,
)


from app.market_intelligence.driver_lane_preference_groups import build_lane_groups


from app.market_intelligence.driver_lane_preference_queries import (
    connect_db,
    get_lane_feedback_rows,
)


def get_driver_lane_preference_status(
    driver_name,
    pickup,
    delivery,
    db_path=SQLITE_DB_FILE,
):
    driver_name = normalize_text(driver_name)
    pickup = normalize_text(pickup)
    delivery = normalize_text(delivery)

    if not is_valid_driver_name(driver_name):
        return {
            "driver_name": driver_name,
            "pickup": pickup,
            "delivery": delivery,
            "status": "UNKNOWN",
            "confidence": "UNKNOWN",
            "sample_size": 0,
            "sample_quality": "UNKNOWN",
            "sample_note": "driver name missing or not checked",
            "can_affect_decision": False,
            "reasons": ["driver name missing or not checked"],
            "feedback_counts": {},
            "lane_group": None,
        }

    if not pickup or not delivery:
        return {
            "driver_name": driver_name,
            "pickup": pickup,
            "delivery": delivery,
            "status": "UNKNOWN",
            "confidence": "UNKNOWN",
            "sample_size": 0,
            "sample_quality": "UNKNOWN",
            "sample_note": "pickup or delivery missing",
            "can_affect_decision": False,
            "reasons": ["pickup or delivery missing"],
            "feedback_counts": {},
            "lane_group": None,
        }

    if not Path(db_path).exists():
        return {
            "driver_name": driver_name,
            "pickup": pickup,
            "delivery": delivery,
            "status": "UNKNOWN",
            "confidence": "UNKNOWN",
            "sample_size": 0,
            "sample_quality": "UNKNOWN",
            "sample_note": "SQLite memory database not found",
            "can_affect_decision": False,
            "reasons": ["SQLite memory database not found"],
            "feedback_counts": {},
            "lane_group": None,
        }

    connection = connect_db(db_path)

    rows = get_lane_feedback_rows(
        connection=connection,
        driver_name=driver_name,
        pickup=pickup,
        delivery=delivery,
        limit=100,
    )

    connection.close()

    lane_groups = build_lane_groups(rows)

    matched_group = None

    for group in lane_groups:
        if (
            normalize_location(group["pickup"]) == normalize_location(pickup)
            and normalize_location(group["delivery"]) == normalize_location(delivery)
        ):
            matched_group = group
            break

    if not matched_group:
        sample_quality = get_sample_quality(0)

        return {
            "driver_name": driver_name,
            "pickup": pickup,
            "delivery": delivery,
            "status": "INSUFFICIENT_LANE_DATA",
            "confidence": "LOW",
            "sample_size": 0,
            "sample_quality": sample_quality["sample_quality"],
            "sample_note": sample_quality["sample_note"],
            "can_affect_decision": sample_quality["can_affect_decision"],
            "reasons": [],
            "feedback_counts": {},
            "lane_group": None,
        }

    classification = classify_lane_signal(matched_group["feedback_counts"])

    return {
        "driver_name": driver_name,
        "pickup": pickup,
        "delivery": delivery,
        "status": classification.get("status", "UNKNOWN"),
        "confidence": classification.get("confidence", "UNKNOWN"),
        "sample_size": classification.get("sample_size", 0),
        "sample_quality": classification.get("sample_quality", "UNKNOWN"),
        "sample_note": classification.get("sample_note", ""),
        "can_affect_decision": classification.get("can_affect_decision", False),
        "reasons": classification.get("reasons", []),
        "feedback_counts": matched_group["feedback_counts"],
        "lane_group": matched_group,
    }
