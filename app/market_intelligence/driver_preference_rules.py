import sqlite3
from pathlib import Path

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


def connect_db(db_path=SQLITE_DB_FILE):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def normalize_driver_name(driver_name):
    return str(driver_name or "").strip()


def is_valid_driver_name(driver_name):
    driver_name = normalize_driver_name(driver_name)

    if not driver_name:
        return False

    if driver_name.upper() in ["UNKNOWN", "NEEDS CHECK", "NONE"]:
        return False

    return True


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


def classify_driver_from_counts(feedback_counts, case_counts):
    booked = feedback_counts.get("booked", 0)
    ratecon_received = feedback_counts.get("ratecon_received", 0)
    sent_to_driver = feedback_counts.get("sent_to_driver", 0)
    driver_rejected = feedback_counts.get("driver_rejected", 0)
    skipped = feedback_counts.get("skipped", 0)
    rate_too_low = feedback_counts.get("rate_too_low", 0)
    bad_broker = feedback_counts.get("bad_broker", 0)

    feedback_items = case_counts.get("feedback_items", 0)
    telegram_alerts = case_counts.get("telegram_alerts", 0)
    load_opportunity_cases = case_counts.get("load_opportunity_cases", 0)
    rate_check_cases = case_counts.get("rate_check_cases", 0)

    reasons = []

    if booked >= 1 or ratecon_received >= 1:
        if booked:
            reasons.append(f"booked feedback {booked}x")

        if ratecon_received:
            reasons.append(f"ratecon_received feedback {ratecon_received}x")

        return {
            "status": "STRONG_POSITIVE",
            "confidence": "MEDIUM",
            "reasons": reasons,
        }

    if sent_to_driver >= 2 and driver_rejected == 0:
        reasons.append(f"sent_to_driver feedback {sent_to_driver}x")

        return {
            "status": "WEAK_POSITIVE",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if driver_rejected >= 2:
        reasons.append(f"driver_rejected feedback {driver_rejected}x")

        return {
            "status": "NEEDS_REVIEW",
            "confidence": "MEDIUM",
            "reasons": reasons,
        }

    if skipped >= 2:
        reasons.append(f"skipped feedback {skipped}x")

        return {
            "status": "NEEDS_REVIEW",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if rate_too_low >= 2:
        reasons.append(f"rate_too_low feedback {rate_too_low}x")

        return {
            "status": "RATE_SENSITIVE",
            "confidence": "MEDIUM",
            "reasons": reasons,
        }

    if bad_broker >= 1 and feedback_items <= 3:
        reasons.append(f"bad_broker feedback {bad_broker}x, should stay broker-side")

        return {
            "status": "INSUFFICIENT_DRIVER_DATA",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if telegram_alerts >= 5 and feedback_items == 0:
        reasons.append(f"{telegram_alerts} Telegram alerts but no feedback")

        return {
            "status": "NEEDS_MORE_FEEDBACK",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if load_opportunity_cases >= 3 and feedback_items == 0:
        reasons.append(f"{load_opportunity_cases} load opportunities but no feedback")

        return {
            "status": "NEEDS_MORE_FEEDBACK",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if rate_check_cases >= 3 and feedback_items == 0:
        reasons.append(f"{rate_check_cases} rate-check cases but no feedback")

        return {
            "status": "NEEDS_MORE_FEEDBACK",
            "confidence": "LOW",
            "reasons": reasons,
        }

    return {
        "status": "INSUFFICIENT_DRIVER_DATA",
        "confidence": "LOW",
        "reasons": [],
    }


def get_driver_preference_status(driver_name, db_path=SQLITE_DB_FILE):
    driver_name = normalize_driver_name(driver_name)

    if not is_valid_driver_name(driver_name):
        return {
            "driver_name": driver_name,
            "status": "UNKNOWN",
            "confidence": "UNKNOWN",
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
        "reasons": classification.get("reasons", []),
        "feedback_counts": feedback_counts,
        "case_counts": case_counts,
        "lane_feedback": lane_feedback,
    }


def format_driver_preference_status(preference_status):
    status = preference_status.get("status", "UNKNOWN")
    confidence = preference_status.get("confidence", "UNKNOWN")
    reasons = preference_status.get("reasons", [])

    if reasons:
        reason_text = "; ".join(reasons)
        return f"{status} / {confidence} — {reason_text}"

    return f"{status} / {confidence}"