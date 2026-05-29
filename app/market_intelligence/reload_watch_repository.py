import json
from copy import deepcopy
from pathlib import Path

from app.market_intelligence.reload_watch_record import normalize_record


RELOAD_WATCH_FILE = "data/reload_watch_records.json"
ACTIVE_WATCH_STATUSES = {"WATCH_ACTIVE", "WATCH_MUTED"}


def record_watch_id(record):
    return str((record or {}).get("watch_id", "")).strip()


def record_status(record):
    return str((record or {}).get("watch_status", "")).strip().upper()


def load_reload_watch_records(file_path=RELOAD_WATCH_FILE):
    path = Path(file_path)

    if not path.exists():
        return []

    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(records, list):
        return []

    return [
        normalize_record(record)
        for record in records
        if isinstance(record, dict)
    ]


def save_reload_watch_records(records, file_path=RELOAD_WATCH_FILE):
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_records = [
        normalize_record(record)
        for record in deepcopy(records or [])
        if isinstance(record, dict)
    ]
    text = json.dumps(
        normalized_records,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    path.write_text(text + "\n", encoding="utf-8")

    return normalized_records


def upsert_reload_watch_record(record, file_path=RELOAD_WATCH_FILE):
    normalized_record = normalize_record(deepcopy(record or {}))
    watch_id = record_watch_id(normalized_record)
    records = load_reload_watch_records(file_path)
    updated_records = []
    replaced = False

    for existing_record in records:
        if watch_id and record_watch_id(existing_record) == watch_id:
            updated_records.append(normalized_record)
            replaced = True
        else:
            updated_records.append(existing_record)

    if not replaced:
        updated_records.append(normalized_record)

    save_reload_watch_records(updated_records, file_path)

    return normalized_record


def get_reload_watch_by_id(watch_id, file_path=RELOAD_WATCH_FILE):
    target_watch_id = str(watch_id or "").strip()

    for record in load_reload_watch_records(file_path):
        if record_watch_id(record) == target_watch_id:
            return record

    return None


def get_active_reload_watches(file_path=RELOAD_WATCH_FILE):
    return [
        record
        for record in load_reload_watch_records(file_path)
        if record_status(record) in ACTIVE_WATCH_STATUSES
    ]
