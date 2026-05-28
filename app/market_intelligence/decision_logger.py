import json
from datetime import datetime, timezone
from pathlib import Path
from app.market_intelligence.decision_run_builder import (
    build_decision_run_record,
    build_run_id,
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
    run_id = build_run_id(
        search_request=search_request,
        loads_count=len(loads),
        timestamp_utc=utc_now_iso(),
    )

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

    run_record = build_decision_run_record(
        search_request=search_request,
        run_id=run_id,
        decision_records=decision_records,
        timestamp_utc=utc_now_iso(),
        recommendation=recommendation,
    )

    append_jsonl(DECISION_RUNS_FILE, [run_record])
    append_jsonl(DECISION_HISTORY_FILE, decision_records)

    return {
        "run_id": run_id,
        "loads_logged": len(decision_records),
        "match_count": run_record["match_count"],
        "review_once_count": run_record["review_once_count"],
        "block_count": run_record["block_count"],
    }
