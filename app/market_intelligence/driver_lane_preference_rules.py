import sqlite3
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


def get_lane_feedback_rows(
    connection,
    driver_name,
    pickup="",
    delivery="",
    broker_mc="",
    feedback="",
    limit=500,
):
    filters = []
    params = []

    if driver_name:
        filters.append("LOWER(c.driver_name) = LOWER(?)")
        params.append(driver_name)

    if pickup:
        filters.append("LOWER(c.pickup) LIKE LOWER(?)")
        params.append(f"%{pickup}%")

    if delivery:
        filters.append("LOWER(c.delivery) LIKE LOWER(?)")
        params.append(f"%{delivery}%")

    if broker_mc:
        filters.append("c.broker_mc = ?")
        params.append(broker_mc)

    if feedback:
        filters.append("LOWER(f.feedback) = LOWER(?)")
        params.append(feedback)

    where_clause = ""

    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    query = f"""
        SELECT
            c.driver_name,
            c.pickup,
            c.delivery,
            f.feedback,

            COUNT(*) AS feedback_count,

            COUNT(DISTINCT c.case_id) AS case_count,
            AVG(c.rate) AS avg_rate,
            AVG(c.total_miles) AS avg_total_miles,
            AVG(c.total_rpm) AS avg_total_rpm,
            AVG(c.weight) AS avg_weight,

            SUM(CASE WHEN c.status = 'BOOKED' THEN 1 ELSE 0 END) AS booked_cases,
            SUM(CASE WHEN c.status = 'RATECON_RECEIVED' THEN 1 ELSE 0 END) AS ratecon_received_cases,
            SUM(CASE WHEN c.status = 'SENT_TO_DRIVER' THEN 1 ELSE 0 END) AS sent_to_driver_cases,
            SUM(CASE WHEN c.status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected_cases,
            SUM(CASE WHEN c.status = 'SKIPPED' THEN 1 ELSE 0 END) AS skipped_cases,
            SUM(CASE WHEN c.status = 'COVERED' THEN 1 ELSE 0 END) AS covered_cases,

            SUM(CASE WHEN c.final_outcome = 'BOOKED' THEN 1 ELSE 0 END) AS final_booked,
            SUM(CASE WHEN c.final_outcome = 'RATECON_RECEIVED' THEN 1 ELSE 0 END) AS final_ratecon_received,
            SUM(CASE WHEN c.final_outcome = 'REJECTED' THEN 1 ELSE 0 END) AS final_rejected,
            SUM(CASE WHEN c.final_outcome = 'SKIPPED' THEN 1 ELSE 0 END) AS final_skipped,
            SUM(CASE WHEN c.final_outcome = 'COVERED' THEN 1 ELSE 0 END) AS final_covered,

            SUM(CASE WHEN c.ai_decision = 'MATCH' THEN 1 ELSE 0 END) AS match_cases,
            SUM(CASE WHEN c.ai_decision = 'REVIEW_ONCE' THEN 1 ELSE 0 END) AS review_once_cases,
            SUM(CASE WHEN c.ai_decision = 'BLOCK' THEN 1 ELSE 0 END) AS blocked_cases,

            SUM(CASE WHEN c.ai_category = 'LOAD OPPORTUNITY' THEN 1 ELSE 0 END) AS load_opportunity_cases,
            SUM(CASE WHEN c.ai_category = 'RATE CHECK' THEN 1 ELSE 0 END) AS rate_check_cases,
            SUM(CASE WHEN c.ai_category = 'BROKER REVIEW' THEN 1 ELSE 0 END) AS broker_review_cases,

            MAX(f.timestamp_utc) AS latest_feedback
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        {where_clause}
        GROUP BY c.driver_name, c.pickup, c.delivery, f.feedback
        ORDER BY feedback_count DESC, latest_feedback DESC
        LIMIT ?
    """

    query_params = list(params)
    query_params.append(limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    return cursor.fetchall()


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
