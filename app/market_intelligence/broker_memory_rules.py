import sqlite3
from pathlib import Path

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


def connect_db(db_path=SQLITE_DB_FILE):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def normalize_mc(broker_mc):
    return str(broker_mc or "").strip()


def is_valid_mc(broker_mc):
    broker_mc = normalize_mc(broker_mc)

    if not broker_mc:
        return False

    if broker_mc.upper() == "NEEDS CHECK":
        return False

    if broker_mc.upper() == "NO MC":
        return False

    return True


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


def classify_broker_from_counts(feedback_counts, case_counts):
    bad_broker_count = feedback_counts.get("bad_broker", 0)
    rate_too_low_count = feedback_counts.get("rate_too_low", 0)
    covered_count = feedback_counts.get("covered", 0)
    booked_count = feedback_counts.get("booked", 0)
    sent_to_driver_count = feedback_counts.get("sent_to_driver", 0)
    ratecon_received_count = feedback_counts.get("ratecon_received", 0)
    called_broker_count = feedback_counts.get("called_broker", 0)

    total_cases = case_counts.get("total_cases", 0)
    rate_check_cases = case_counts.get("rate_check_cases", 0)
    load_opportunity_cases = case_counts.get("load_opportunity_cases", 0)
    telegram_alerts = case_counts.get("telegram_alerts", 0)

    reasons = []

    if bad_broker_count >= 2:
        reasons.append(f"bad_broker feedback {bad_broker_count}x")
        return {
            "status": "BAD_BROKER_REVIEW",
            "risk_level": "HIGH",
            "reasons": reasons,
        }

    if rate_too_low_count >= 2:
        reasons.append(f"rate_too_low feedback {rate_too_low_count}x")
        return {
            "status": "RATE_NEGOTIATION_REQUIRED",
            "risk_level": "MEDIUM",
            "reasons": reasons,
        }

    if covered_count >= 2:
        reasons.append(f"covered feedback {covered_count}x")
        return {
            "status": "WATCHLIST",
            "risk_level": "MEDIUM",
            "reasons": reasons,
        }

    if booked_count >= 1 or ratecon_received_count >= 1:
        if booked_count:
            reasons.append(f"booked feedback {booked_count}x")

        if ratecon_received_count:
            reasons.append(f"ratecon_received feedback {ratecon_received_count}x")

        return {
            "status": "GOOD",
            "risk_level": "LOW",
            "reasons": reasons,
        }

    if sent_to_driver_count >= 2:
        reasons.append(f"sent_to_driver feedback {sent_to_driver_count}x")
        return {
            "status": "GOOD",
            "risk_level": "LOW",
            "reasons": reasons,
        }

    if called_broker_count >= 2 and rate_check_cases >= 1:
        reasons.append(f"called_broker feedback {called_broker_count}x on rate-check activity")
        return {
            "status": "WATCHLIST",
            "risk_level": "LOW",
            "reasons": reasons,
        }

    if total_cases >= 3 and telegram_alerts == 0:
        reasons.append(f"{total_cases} cases but no Telegram alerts")
        return {
            "status": "LOW_RELEVANCE",
            "risk_level": "LOW",
            "reasons": reasons,
        }

    if rate_check_cases >= 3 and load_opportunity_cases == 0:
        reasons.append(f"{rate_check_cases} rate-check cases and no load opportunities")
        return {
            "status": "RATE_NEGOTIATION_REQUIRED",
            "risk_level": "MEDIUM",
            "reasons": reasons,
        }

    return {
        "status": "UNKNOWN",
        "risk_level": "UNKNOWN",
        "reasons": [],
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


def format_broker_memory_status(memory_status):
    status = memory_status.get("status", "UNKNOWN")
    risk_level = memory_status.get("risk_level", "UNKNOWN")
    reasons = memory_status.get("reasons", [])

    if reasons:
        reason_text = "; ".join(reasons)
        return f"{status} / {risk_level} вЂ” {reason_text}"

    return f"{status} / {risk_level}"
