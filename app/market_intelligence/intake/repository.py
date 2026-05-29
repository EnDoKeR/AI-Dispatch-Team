import json
from copy import deepcopy
from pathlib import Path

from app.market_intelligence.intake.record import build_intake_record


INTAKE_RECORDS_FILE = "data/intake_records.json"


def normalize_repository_record(record):
    normalized_record = build_intake_record(deepcopy(record or {}))

    if isinstance(record, dict) and "status" in record:
        normalized_record["status"] = str(record.get("status") or "").strip().upper()

    return normalized_record


def record_intake_id(record):
    return str((record or {}).get("intake_id", "")).strip()


def record_status(record):
    return str((record or {}).get("status", "")).strip().upper()


def load_intake_records(file_path=INTAKE_RECORDS_FILE):
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
        normalize_repository_record(record)
        for record in records
        if isinstance(record, dict)
    ]


def save_intake_records(records, file_path=INTAKE_RECORDS_FILE):
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_records = [
        normalize_repository_record(record)
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


def upsert_intake_record(record, file_path=INTAKE_RECORDS_FILE):
    normalized_record = normalize_repository_record(record)
    intake_id = record_intake_id(normalized_record)
    records = load_intake_records(file_path)
    updated_records = []
    replaced = False

    for existing_record in records:
        if intake_id and record_intake_id(existing_record) == intake_id:
            updated_records.append(normalized_record)
            replaced = True
        else:
            updated_records.append(existing_record)

    if not replaced:
        updated_records.append(normalized_record)

    save_intake_records(updated_records, file_path)

    return normalized_record


def get_intake_record_by_id(intake_id, file_path=INTAKE_RECORDS_FILE):
    target_intake_id = str(intake_id or "").strip()

    for record in load_intake_records(file_path):
        if record_intake_id(record) == target_intake_id:
            return record

    return None


def get_intake_records_by_status(status, file_path=INTAKE_RECORDS_FILE):
    target_status = str(status or "").strip().upper()

    return [
        record
        for record in load_intake_records(file_path)
        if record_status(record) == target_status
    ]
