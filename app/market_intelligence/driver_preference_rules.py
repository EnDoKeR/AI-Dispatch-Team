import sqlite3
from pathlib import Path

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


def connect_db(db_path=SQLITE_DB_FILE):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


from app.market_intelligence.driver_preference_core import (
    classify_driver_from_counts,
    feedback_sample_size,
    format_driver_preference_status,
    get_sample_quality,
    is_valid_driver_name,
    normalize_driver_name,
)


def get_driver_feedback_counts(connection, driver_name):
    driver_name = normalize_driver_name(driver_name)

    if not is_valid_driver_name(driver_name):
        return {}

    query = """
        SELECT
            f.feedback,
            COUNT(*) AS count
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        WHERE LOWER(c.driver_name) = LOWER(?)
        GROUP BY f.feedback
    """

    cursor = connection.cursor()
    cursor.execute(query, (driver_name,))
    rows = cursor.fetchall()

    return {
        row["feedback"]: row["count"]
        for row in rows
    }


def get_driver_case_counts(connection, driver_name):
    driver_name = normalize_driver_name(driver_name)

    if not is_valid_driver_name(driver_name):
        return {}

    query = """
        SELECT
            COUNT(*) AS total_cases,

            SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS open_cases,
            SUM(CASE WHEN status = 'CALLED' THEN 1 ELSE 0 END) AS called_cases,
            SUM(CASE WHEN status = 'SENT_TO_DRIVER' THEN 1 ELSE 0 END) AS sent_to_driver_cases,
            SUM(CASE WHEN status = 'BOOKED' THEN 1 ELSE 0 END) AS booked_cases,
            SUM(CASE WHEN status = 'RATECON_RECEIVED' THEN 1 ELSE 0 END) AS ratecon_received_cases,
            SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected_cases,
            SUM(CASE WHEN status = 'SKIPPED' THEN 1 ELSE 0 END) AS skipped_cases,
            SUM(CASE WHEN status = 'COVERED' THEN 1 ELSE 0 END) AS covered_cases,

            SUM(CASE WHEN final_outcome = 'BOOKED' THEN 1 ELSE 0 END) AS final_booked,
            SUM(CASE WHEN final_outcome = 'RATECON_RECEIVED' THEN 1 ELSE 0 END) AS final_ratecon_received,
            SUM(CASE WHEN final_outcome = 'REJECTED' THEN 1 ELSE 0 END) AS final_rejected,
            SUM(CASE WHEN final_outcome = 'SKIPPED' THEN 1 ELSE 0 END) AS final_skipped,
            SUM(CASE WHEN final_outcome = 'COVERED' THEN 1 ELSE 0 END) AS final_covered,

            SUM(CASE WHEN ai_decision = 'MATCH' THEN 1 ELSE 0 END) AS match_cases,
            SUM(CASE WHEN ai_decision = 'REVIEW_ONCE' THEN 1 ELSE 0 END) AS review_once_cases,
            SUM(CASE WHEN ai_decision = 'BLOCK' THEN 1 ELSE 0 END) AS blocked_cases,

            SUM(CASE WHEN ai_category = 'LOAD OPPORTUNITY' THEN 1 ELSE 0 END) AS load_opportunity_cases,
            SUM(CASE WHEN ai_category = 'RATE CHECK' THEN 1 ELSE 0 END) AS rate_check_cases,
            SUM(CASE WHEN ai_category = 'BROKER REVIEW' THEN 1 ELSE 0 END) AS broker_review_cases,
            SUM(CASE WHEN ai_category = 'CONESTOGA VERIFY' THEN 1 ELSE 0 END) AS conestoga_verify_cases,

            SUM(telegram_alert_count) AS telegram_alerts,
            SUM(dispatcher_feedback_count) AS feedback_items,
            SUM(ratecon_count) AS ratecons
        FROM dispatch_cases
        WHERE LOWER(driver_name) = LOWER(?)
    """

    cursor = connection.cursor()
    cursor.execute(query, (driver_name,))
    row = cursor.fetchone()

    if not row:
        return {}

    return {
        "total_cases": row["total_cases"] or 0,
        "open_cases": row["open_cases"] or 0,
        "called_cases": row["called_cases"] or 0,
        "sent_to_driver_cases": row["sent_to_driver_cases"] or 0,
        "booked_cases": row["booked_cases"] or 0,
        "ratecon_received_cases": row["ratecon_received_cases"] or 0,
        "rejected_cases": row["rejected_cases"] or 0,
        "skipped_cases": row["skipped_cases"] or 0,
        "covered_cases": row["covered_cases"] or 0,
        "final_booked": row["final_booked"] or 0,
        "final_ratecon_received": row["final_ratecon_received"] or 0,
        "final_rejected": row["final_rejected"] or 0,
        "final_skipped": row["final_skipped"] or 0,
        "final_covered": row["final_covered"] or 0,
        "match_cases": row["match_cases"] or 0,
        "review_once_cases": row["review_once_cases"] or 0,
        "blocked_cases": row["blocked_cases"] or 0,
        "load_opportunity_cases": row["load_opportunity_cases"] or 0,
        "rate_check_cases": row["rate_check_cases"] or 0,
        "broker_review_cases": row["broker_review_cases"] or 0,
        "conestoga_verify_cases": row["conestoga_verify_cases"] or 0,
        "telegram_alerts": row["telegram_alerts"] or 0,
        "feedback_items": row["feedback_items"] or 0,
        "ratecons": row["ratecons"] or 0,
    }


def get_driver_lane_feedback(connection, driver_name, limit=20):
    driver_name = normalize_driver_name(driver_name)

    if not is_valid_driver_name(driver_name):
        return []

    query = """
        SELECT
            c.pickup,
            c.delivery,
            f.feedback,
            COUNT(*) AS count,
            AVG(c.rate) AS avg_rate,
            AVG(c.total_rpm) AS avg_rpm,
            AVG(c.total_miles) AS avg_total_miles
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        WHERE LOWER(c.driver_name) = LOWER(?)
        GROUP BY c.pickup, c.delivery, f.feedback
        ORDER BY count DESC, c.pickup ASC, c.delivery ASC
        LIMIT ?
    """

    cursor = connection.cursor()
    cursor.execute(query, (driver_name, limit))
    return cursor.fetchall()

def get_driver_preference_status(driver_name, db_path=SQLITE_DB_FILE):
    driver_name = normalize_driver_name(driver_name)

    if not is_valid_driver_name(driver_name):
        return {
            "driver_name": driver_name,
            "status": "UNKNOWN",
            "confidence": "UNKNOWN",
            "sample_size": 0,
            "sample_quality": "UNKNOWN",
            "sample_note": "driver name missing or not checked",
            "can_affect_decision": False,
            "reasons": ["driver name missing or not checked"],
            "feedback_counts": {},
            "case_counts": {},
            "lane_feedback": [],
        }

    if not Path(db_path).exists():
        return {
            "driver_name": driver_name,
            "status": "UNKNOWN",
            "confidence": "UNKNOWN",
            "sample_size": 0,
            "sample_quality": "UNKNOWN",
            "sample_note": "SQLite memory database not found",
            "can_affect_decision": False,
            "reasons": ["SQLite memory database not found"],
            "feedback_counts": {},
            "case_counts": {},
            "lane_feedback": [],
        }

    connection = connect_db(db_path)

    feedback_counts = get_driver_feedback_counts(connection, driver_name)
    case_counts = get_driver_case_counts(connection, driver_name)
    lane_feedback = get_driver_lane_feedback(connection, driver_name)

    connection.close()

    classification = classify_driver_from_counts(
        feedback_counts=feedback_counts,
        case_counts=case_counts,
    )

    return {
        "driver_name": driver_name,
        "status": classification.get("status", "UNKNOWN"),
        "confidence": classification.get("confidence", "UNKNOWN"),
        "sample_size": classification.get("sample_size", 0),
        "sample_quality": classification.get("sample_quality", "UNKNOWN"),
        "sample_note": classification.get("sample_note", ""),
        "can_affect_decision": classification.get("can_affect_decision", False),
        "reasons": classification.get("reasons", []),
        "feedback_counts": feedback_counts,
        "case_counts": case_counts,
        "lane_feedback": lane_feedback,
    }
