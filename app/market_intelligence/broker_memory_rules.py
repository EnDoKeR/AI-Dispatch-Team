from pathlib import Path

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE

from app.market_intelligence.broker_memory_core import (
    classify_broker_from_counts,
    format_broker_memory_status,
    is_valid_mc,
    normalize_mc,
)

from app.market_intelligence.broker_memory_queries import (
    connect_db,
    get_broker_case_counts,
    get_broker_feedback_counts,
)


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
