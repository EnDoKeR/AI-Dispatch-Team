from app.market_intelligence.decision_logger_helpers import (
    safe_value,
    stable_text_hash,
)


def build_run_id(search_request, loads_count, timestamp_utc):
    run_id_base = "|".join(
        [
            timestamp_utc,
            str(getattr(search_request, "driver_name", "")),
            str(getattr(search_request, "current_location", "")),
            str(loads_count),
        ]
    )

    return f"RUN-{stable_text_hash(run_id_base)}"


def count_decisions(decision_records):
    match_count = len(
        [record for record in decision_records if record["decision"] == "MATCH"]
    )

    review_once_count = len(
        [record for record in decision_records if record["decision"] == "REVIEW_ONCE"]
    )

    block_count = len(
        [record for record in decision_records if record["decision"] == "BLOCK"]
    )

    return {
        "match_count": match_count,
        "review_once_count": review_once_count,
        "block_count": block_count,
    }


def build_decision_run_record(
    search_request,
    run_id,
    decision_records,
    timestamp_utc,
    recommendation=None,
):
    recommendation = recommendation or {}
    counts = count_decisions(decision_records)

    return {
        "timestamp_utc": timestamp_utc,
        "run_id": run_id,
        "driver_name": safe_value(getattr(search_request, "driver_name", "")),
        "driver_location": safe_value(getattr(search_request, "current_location", "")),
        "driver_equipment": safe_value(getattr(search_request, "equipment", "")),
        "target_direction": safe_value(getattr(search_request, "target_direction", "")),
        "loads_analyzed": len(decision_records),
        "match_count": counts["match_count"],
        "review_once_count": counts["review_once_count"],
        "block_count": counts["block_count"],
        "market_activity": safe_value(recommendation.get("market_activity", "")),
        "market_driver_fit": safe_value(recommendation.get("driver_fit", "")),
        "market_action_status": safe_value(recommendation.get("action_status", "")),
    }
