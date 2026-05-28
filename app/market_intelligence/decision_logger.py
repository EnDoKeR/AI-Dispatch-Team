import json
from datetime import datetime, timezone
from pathlib import Path
from app.market_intelligence.decision_logger_helpers import (
    safe_value,
    stable_text_hash,
)
from app.market_intelligence.decision_serializer import serialize_load_decision


DECISION_HISTORY_FILE = Path("data/decision_history.jsonl")
DECISION_RUNS_FILE = Path("data/decision_runs.jsonl")


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()




def append_jsonl(file_path, records):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "a", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_decisions(search_request, loads, recommendation=None):
    run_id_base = "|".join(
        [
            utc_now_iso(),
            str(getattr(search_request, "driver_name", "")),
            str(getattr(search_request, "current_location", "")),
            str(len(loads)),
        ]
    )

    run_id = f"RUN-{stable_text_hash(run_id_base)}"

    decision_records = []

    for load in loads:
        decision_records.append(
            serialize_load_decision(
                load=load,
                search_request=search_request,
                run_id=run_id,
                timestamp_utc=utc_now_iso(),
                recommendation=recommendation,
            )
        )

    match_count = len(
        [record for record in decision_records if record["decision"] == "MATCH"]
    )

    review_count = len(
        [record for record in decision_records if record["decision"] == "REVIEW_ONCE"]
    )

    block_count = len(
        [record for record in decision_records if record["decision"] == "BLOCK"]
    )

    run_record = {
        "timestamp_utc": utc_now_iso(),
        "run_id": run_id,
        "driver_name": safe_value(getattr(search_request, "driver_name", "")),
        "driver_location": safe_value(getattr(search_request, "current_location", "")),
        "driver_equipment": safe_value(getattr(search_request, "equipment", "")),
        "target_direction": safe_value(getattr(search_request, "target_direction", "")),
        "loads_analyzed": len(decision_records),
        "match_count": match_count,
        "review_once_count": review_count,
        "block_count": block_count,
        "market_activity": safe_value((recommendation or {}).get("market_activity", "")),
        "market_driver_fit": safe_value((recommendation or {}).get("driver_fit", "")),
        "market_action_status": safe_value((recommendation or {}).get("action_status", "")),
    }

    append_jsonl(DECISION_RUNS_FILE, [run_record])
    append_jsonl(DECISION_HISTORY_FILE, decision_records)

    return {
        "run_id": run_id,
        "loads_logged": len(decision_records),
        "match_count": match_count,
        "review_once_count": review_count,
        "block_count": block_count,
    }
