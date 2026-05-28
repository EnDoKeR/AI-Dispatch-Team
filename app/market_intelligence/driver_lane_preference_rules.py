import sqlite3
from pathlib import Path

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


POSITIVE_FEEDBACK = {
    "booked",
    "ratecon_received",
    "sent_to_driver",
}

RATE_FEEDBACK = {
    "rate_too_low",
}

BROKER_FEEDBACK = {
    "bad_broker",
    "called_broker",
}

MARKET_FEEDBACK = {
    "covered",
}

NEGATIVE_OR_UNCLEAR_FEEDBACK = {
    "skipped",
    "driver_rejected",
    "not_interested",
    "other",
}


def connect_db(db_path=SQLITE_DB_FILE):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def normalize_text(value):
    return str(value or "").strip()


def normalize_location(value):
    return normalize_text(value).lower()


def is_valid_driver_name(driver_name):
    driver_name = normalize_text(driver_name)

    if not driver_name:
        return False

    if driver_name.upper() in ["UNKNOWN", "NEEDS CHECK", "NONE"]:
        return False

    return True


def average(values):
    if not values:
        return 0

    return sum(values) / len(values)


def classify_lane_signal(feedback_counts):
    positive_count = sum(feedback_counts.get(item, 0) for item in POSITIVE_FEEDBACK)
    rate_count = sum(feedback_counts.get(item, 0) for item in RATE_FEEDBACK)
    broker_count = sum(feedback_counts.get(item, 0) for item in BROKER_FEEDBACK)
    market_count = sum(feedback_counts.get(item, 0) for item in MARKET_FEEDBACK)
    negative_count = sum(
        feedback_counts.get(item, 0)
        for item in NEGATIVE_OR_UNCLEAR_FEEDBACK
    )

    reasons = []

    if positive_count >= 2 and rate_count >= 1:
        reasons.append(f"positive feedback {positive_count}x")
        reasons.append(f"rate feedback {rate_count}x")

        return {
            "status": "POSITIVE_LANE_WITH_RATE_SENSITIVITY",
            "confidence": "MEDIUM",
            "reasons": reasons,
        }

    if positive_count >= 2:
        reasons.append(f"positive feedback {positive_count}x")

        return {
            "status": "POSITIVE_LANE",
            "confidence": "MEDIUM",
            "reasons": reasons,
        }

    if broker_count >= 2:
        reasons.append(f"broker/workflow feedback {broker_count}x")

        return {
            "status": "BROKER_ISSUE_NOT_DRIVER_PREFERENCE",
            "confidence": "MEDIUM",
            "reasons": reasons,
        }

    if rate_count >= 2:
        reasons.append(f"rate feedback {rate_count}x")

        return {
            "status": "RATE_SENSITIVE_LANE",
            "confidence": "MEDIUM",
            "reasons": reasons,
        }

    if market_count >= 1 and positive_count == 0:
        reasons.append(f"market timing feedback {market_count}x")

        return {
            "status": "MARKET_TIMING_SIGNAL",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if negative_count >= 2:
        reasons.append(f"negative/unclear feedback {negative_count}x")

        return {
            "status": "NEEDS_DRIVER_OR_DISPATCH_REVIEW",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if positive_count == 1:
        reasons.append("single positive feedback")

        return {
            "status": "WEAK_POSITIVE_LANE",
            "confidence": "LOW",
            "reasons": reasons,
        }

    return {
        "status": "INSUFFICIENT_LANE_DATA",
        "confidence": "LOW",
        "reasons": [],
    }


def format_lane_preference_status(classification):
    status = classification.get("status", "UNKNOWN")
    confidence = classification.get("confidence", "UNKNOWN")
    reasons = classification.get("reasons", [])

    if reasons:
        return f"{status} / {confidence} — {'; '.join(reasons)}"

    return f"{status} / {confidence}"


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


def build_lane_groups(rows):
    lane_groups = {}

    for row in rows:
        key = (
            row["driver_name"] or "UNKNOWN",
            row["pickup"] or "UNKNOWN",
            row["delivery"] or "UNKNOWN",
        )

        if key not in lane_groups:
            lane_groups[key] = {
                "driver_name": key[0],
                "pickup": key[1],
                "delivery": key[2],
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

        group = lane_groups[key]
        feedback = row["feedback"] or "UNKNOWN"

        group["feedback_counts"][feedback] = (
            group["feedback_counts"].get(feedback, 0)
            + (row["feedback_count"] or 0)
        )

        group["case_count"] += row["case_count"] or 0

        if row["avg_rate"] is not None:
            group["avg_rate_values"].append(row["avg_rate"])

        if row["avg_total_miles"] is not None:
            group["avg_miles_values"].append(row["avg_total_miles"])

        if row["avg_total_rpm"] is not None:
            group["avg_rpm_values"].append(row["avg_total_rpm"])

        if row["avg_weight"] is not None:
            group["avg_weight_values"].append(row["avg_weight"])

        for field_name in [
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
        ]:
            group[field_name] += row[field_name] or 0

        latest_feedback = row["latest_feedback"] or ""

        if latest_feedback > group["latest_feedback"]:
            group["latest_feedback"] = latest_feedback

    return list(lane_groups.values())


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
        return {
            "driver_name": driver_name,
            "pickup": pickup,
            "delivery": delivery,
            "status": "INSUFFICIENT_LANE_DATA",
            "confidence": "LOW",
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
        "reasons": classification.get("reasons", []),
        "feedback_counts": matched_group["feedback_counts"],
        "lane_group": matched_group,
    }


def format_driver_lane_preference_status(preference_status):
    status = preference_status.get("status", "UNKNOWN")
    confidence = preference_status.get("confidence", "UNKNOWN")
    reasons = preference_status.get("reasons", [])

    if reasons:
        return f"{status} / {confidence} — {'; '.join(reasons)}"

    return f"{status} / {confidence}"