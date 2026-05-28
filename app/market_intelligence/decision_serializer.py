from app.market_intelligence.decision_logger_helpers import (
    build_load_id,
    build_reason_list,
    get_decision,
    get_decision_category,
    safe_value,
)


def serialize_load_decision(load, search_request, run_id, timestamp_utc, recommendation=None):
    recommendation = recommendation or {}

    decision = get_decision(load)
    category = get_decision_category(load)
    reasons = build_reason_list(load)

    is_good = False
    is_qualified = False

    if hasattr(load, "is_good") and callable(load.is_good):
        is_good = bool(load.is_good())

    if hasattr(load, "is_qualified") and callable(load.is_qualified):
        is_qualified = bool(load.is_qualified())

    return {
        "timestamp_utc": timestamp_utc,
        "run_id": run_id,

        "driver_name": safe_value(getattr(search_request, "driver_name", "")),
        "driver_location": safe_value(getattr(search_request, "current_location", "")),
        "driver_equipment": safe_value(getattr(search_request, "equipment", "")),
        "driver_max_weight": safe_value(getattr(search_request, "max_weight", 0)),
        "target_direction": safe_value(getattr(search_request, "target_direction", "")),
        "target_city": safe_value(getattr(search_request, "target_city", "")),

        "load_id": build_load_id(load),
        "pickup": safe_value(getattr(load, "pickup", "")),
        "delivery": safe_value(getattr(load, "delivery", "")),
        "rate": safe_value(getattr(load, "rate", 0)),
        "loaded_miles": safe_value(getattr(load, "loaded_miles", 0)),
        "empty_miles": safe_value(getattr(load, "empty_miles", 0)),
        "total_miles": safe_value(getattr(load, "total_miles", 0)),
        "total_rpm": safe_value(getattr(load, "total_rpm", 0)),
        "weight": safe_value(getattr(load, "weight", 0)),
        "posted_trailer_type": safe_value(getattr(load, "posted_trailer_type", "")),
        "commodity": safe_value(getattr(load, "commodity", "")),
        "pickup_time": safe_value(getattr(load, "pickup_time", "")),
        "delivery_time": safe_value(getattr(load, "delivery_time", "")),

        "broker_name": safe_value(getattr(load, "broker_name", "")),
        "broker_mc": safe_value(getattr(load, "broker_mc", "")),
        "broker_contact": safe_value(getattr(load, "broker_contact", "")),
        "reference_id": safe_value(getattr(load, "reference_id", "")),
        "broker_status": safe_value(getattr(load, "broker_status", "")),
        "credit_score": safe_value(getattr(load, "credit_score", "")),
        "days_to_pay": safe_value(getattr(load, "days_to_pay", "")),

        "decision": decision,
        "category": category,
        "score": load.opportunity_score() if hasattr(load, "opportunity_score") else 0,
        "priority": load.priority() if hasattr(load, "priority") else "",
        "suggested_action": load.suggested_action() if hasattr(load, "suggested_action") else "",

        "is_good": is_good,
        "is_qualified": is_qualified,
        "target_relation": safe_value(getattr(load, "target_relation", "")),
        "driver_fit_status": safe_value(getattr(load, "driver_fit_status", "")),
        "driver_match_status": safe_value(getattr(load, "driver_match_status", "")),

        "reasons": reasons,
        "notes": safe_value(getattr(load, "notes", "")),

        "market_activity": safe_value(recommendation.get("market_activity", "")),
        "market_driver_fit": safe_value(recommendation.get("driver_fit", "")),
        "market_action_status": safe_value(recommendation.get("action_status", "")),
        "market_best_bucket": safe_value(recommendation.get("best_bucket", "")),

        "telegram_sent": None,
        "dispatcher_feedback": None,
        "final_result": None,
        "final_notes": None,
    }
