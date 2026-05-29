from pathlib import Path

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE

from app.market_intelligence.driver_preference_core import (
    classify_driver_from_counts,
    feedback_sample_size,
    format_driver_preference_status,
    get_sample_quality,
    is_valid_driver_name,
    normalize_driver_name,
)

from app.market_intelligence.driver_preference_queries import (
    connect_db,
    get_driver_case_counts,
    get_driver_feedback_counts,
    get_driver_lane_feedback,
)


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
