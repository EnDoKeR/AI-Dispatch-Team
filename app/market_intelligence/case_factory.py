from app.market_intelligence.case_id_resolver import build_case_id


def safe(value, default=""):
    if value is None:
        return default

    return value


def build_case_from_decision(decision_record):
    case_id = build_case_id(
        driver_name=decision_record.get("driver_name", ""),
        load_id=decision_record.get("load_id", ""),
        reference_id=decision_record.get("reference_id", ""),
        broker_mc=decision_record.get("broker_mc", ""),
    )

    return {
        "case_id": case_id,
        "created_at_utc": decision_record.get("timestamp_utc", ""),
        "updated_at_utc": decision_record.get("timestamp_utc", ""),

        "status": "OPEN",
        "final_outcome": None,

        "driver_name": safe(decision_record.get("driver_name", "")),
        "driver_location": safe(decision_record.get("driver_location", "")),
        "driver_equipment": safe(decision_record.get("driver_equipment", "")),

        "load_id": safe(decision_record.get("load_id", "")),
        "reference_id": safe(decision_record.get("reference_id", "")),

        "pickup": safe(decision_record.get("pickup", "")),
        "delivery": safe(decision_record.get("delivery", "")),
        "rate": safe(decision_record.get("rate", 0)),
        "loaded_miles": safe(decision_record.get("loaded_miles", 0)),
        "empty_miles": safe(decision_record.get("empty_miles", 0)),
        "total_miles": safe(decision_record.get("total_miles", 0)),
        "total_rpm": safe(decision_record.get("total_rpm", 0)),
        "weight": safe(decision_record.get("weight", 0)),
        "posted_trailer_type": safe(decision_record.get("posted_trailer_type", "")),
        "commodity": safe(decision_record.get("commodity", "")),

        "broker_name": safe(decision_record.get("broker_name", "")),
        "broker_mc": safe(decision_record.get("broker_mc", "")),
        "broker_contact": safe(decision_record.get("broker_contact", "")),
        "broker_status": safe(decision_record.get("broker_status", "")),
        "credit_score": safe(decision_record.get("credit_score", "")),
        "days_to_pay": safe(decision_record.get("days_to_pay", "")),

        "ai_decision": {
            "decision": safe(decision_record.get("decision", "")),
            "category": safe(decision_record.get("category", "")),
            "score": safe(decision_record.get("score", 0)),
            "priority": safe(decision_record.get("priority", "")),
            "suggested_action": safe(decision_record.get("suggested_action", "")),
            "reasons": decision_record.get("reasons", []),
            "timestamp_utc": decision_record.get("timestamp_utc", ""),
        },

        "telegram_alerts": [],
        "dispatcher_feedback": [],
        "ratecons": [],
        "events_count": 0,
    }


def build_case_from_outbox(outbox_record):
    case_id = build_case_id(
        driver_name=outbox_record.get("driver_name", ""),
        load_id="",
        reference_id=outbox_record.get("reference_id", ""),
        broker_mc=outbox_record.get("broker_mc", ""),
    )

    return {
        "case_id": case_id,
        "created_at_utc": outbox_record.get("timestamp_utc", ""),
        "updated_at_utc": outbox_record.get("timestamp_utc", ""),

        "status": "OPEN",
        "final_outcome": None,

        "driver_name": safe(outbox_record.get("driver_name", "")),
        "driver_location": "",
        "driver_equipment": "",

        "load_id": "",
        "reference_id": safe(outbox_record.get("reference_id", "")),

        "pickup": safe(outbox_record.get("pickup", "")),
        "delivery": safe(outbox_record.get("delivery", "")),
        "rate": safe(outbox_record.get("rate", "")),
        "loaded_miles": 0,
        "empty_miles": 0,
        "total_miles": 0,
        "total_rpm": 0,
        "weight": 0,
        "posted_trailer_type": "",
        "commodity": "",

        "broker_name": safe(outbox_record.get("broker", "")),
        "broker_mc": safe(outbox_record.get("broker_mc", "")),
        "broker_contact": "",
        "broker_status": "",
        "credit_score": "",
        "days_to_pay": "",

        "ai_decision": {
            "decision": "",
            "category": safe(outbox_record.get("category", "")),
            "score": 0,
            "priority": "",
            "suggested_action": "",
            "reasons": [],
            "timestamp_utc": "",
        },

        "telegram_alerts": [],
        "dispatcher_feedback": [],
        "ratecons": [],
        "events_count": 0,
    }
