import sqlite3
from pathlib import Path

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


def connect_db(db_path=SQLITE_DB_FILE):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


from app.market_intelligence.broker_memory_core import (
    classify_broker_from_counts,
    format_broker_memory_status,
    is_valid_mc,
    normalize_mc,
)


def get_broker_feedback_counts(connection, broker_mc):
    broker_mc = normalize_mc(broker_mc)

    if not is_valid_mc(broker_mc):
        return {}

    query = """
        SELECT
            f.feedback,
            COUNT(*) AS count
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        WHERE c.broker_mc = ?
        GROUP BY f.feedback
    """

    cursor = connection.cursor()
    cursor.execute(query, (broker_mc,))
    rows = cursor.fetchall()

    counts = {}

    for row in rows:
        counts[row["feedback"]] = row["count"]

    return counts


def get_broker_case_counts(connection, broker_mc):
    broker_mc = normalize_mc(broker_mc)

    if not is_valid_mc(broker_mc):
        return {}

    query = """
        SELECT
            COUNT(*) AS total_cases,

            SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS open_cases,
            SUM(CASE WHEN status = 'COVERED' THEN 1 ELSE 0 END) AS covered_cases,
            SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected_cases,
            SUM(CASE WHEN status = 'RATECON_RECEIVED' THEN 1 ELSE 0 END) AS ratecon_received_cases,
            SUM(CASE WHEN status = 'SENT_TO_DRIVER' THEN 1 ELSE 0 END) AS sent_to_driver_cases,
            SUM(CASE WHEN status = 'BOOKED' THEN 1 ELSE 0 END) AS booked_cases,

            SUM(CASE WHEN ai_category = 'LOAD OPPORTUNITY' THEN 1 ELSE 0 END) AS load_opportunity_cases,
            SUM(CASE WHEN ai_category = 'RATE CHECK' THEN 1 ELSE 0 END) AS rate_check_cases,
            SUM(CASE WHEN ai_category = 'CONESTOGA VERIFY' THEN 1 ELSE 0 END) AS conestoga_verify_cases,
            SUM(CASE WHEN ai_category = 'OD / PERMIT' THEN 1 ELSE 0 END) AS od_permit_cases,
            SUM(CASE WHEN ai_category = 'BLOCK' THEN 1 ELSE 0 END) AS blocked_cases,

            SUM(telegram_alert_count) AS telegram_alerts,
            SUM(dispatcher_feedback_count) AS feedback_items,
            SUM(ratecon_count) AS ratecons
        FROM dispatch_cases
        WHERE broker_mc = ?
    """

    cursor = connection.cursor()
    cursor.execute(query, (broker_mc,))
    row = cursor.fetchone()

    if not row:
        return {}

    return {
        "total_cases": row["total_cases"] or 0,
        "open_cases": row["open_cases"] or 0,
        "covered_cases": row["covered_cases"] or 0,
        "rejected_cases": row["rejected_cases"] or 0,
        "ratecon_received_cases": row["ratecon_received_cases"] or 0,
        "sent_to_driver_cases": row["sent_to_driver_cases"] or 0,
        "booked_cases": row["booked_cases"] or 0,
        "load_opportunity_cases": row["load_opportunity_cases"] or 0,
        "rate_check_cases": row["rate_check_cases"] or 0,
        "conestoga_verify_cases": row["conestoga_verify_cases"] or 0,
        "od_permit_cases": row["od_permit_cases"] or 0,
        "blocked_cases": row["blocked_cases"] or 0,
        "telegram_alerts": row["telegram_alerts"] or 0,
        "feedback_items": row["feedback_items"] or 0,
        "ratecons": row["ratecons"] or 0,
    }


def get_broker_memory_status(broker_mc, db_path=SQLITE_DB_FILE):
    broker_mc = normalize_mc(broker_mc)

    if not is_valid_mc(broker_mc):
        return {
            "broker_mc": broker_mc,
            "status": "UNKNOWN",
            "risk_level": "UNKNOWN",
            "reasons": ["broker MC missing or not checked"],
            "feedback_counts": {},
            "case_counts": {},
        }

    if not Path(db_path).exists():
        return {
            "broker_mc": broker_mc,
            "status": "UNKNOWN",
            "risk_level": "UNKNOWN",
            "reasons": ["SQLite memory database not found"],
            "feedback_counts": {},
            "case_counts": {},
        }

    connection = connect_db(db_path)

    feedback_counts = get_broker_feedback_counts(connection, broker_mc)
    case_counts = get_broker_case_counts(connection, broker_mc)

    connection.close()

    classification = classify_broker_from_counts(
        feedback_counts=feedback_counts,
        case_counts=case_counts,
    )

    return {
        "broker_mc": broker_mc,
        "status": classification.get("status", "UNKNOWN"),
        "risk_level": classification.get("risk_level", "UNKNOWN"),
        "reasons": classification.get("reasons", []),
        "feedback_counts": feedback_counts,
        "case_counts": case_counts,
    }
