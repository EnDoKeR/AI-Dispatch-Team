import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


DISPATCH_EVENTS_FILE = Path("data/dispatch_events.jsonl")


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def stable_hash(text):
    text = str(text or "").strip().lower()
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def append_jsonl(file_path, records):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "a", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_event_id(case_id, event_type, timestamp_utc, extra_text=""):
    base = "|".join(
        [
            str(case_id or ""),
            str(event_type or ""),
            str(timestamp_utc or ""),
            str(extra_text or ""),
        ]
    )

    return f"EVT-{stable_hash(base)}"


def build_dispatch_event(
    case_id,
    event_type,
    driver_name="",
    load_id="",
    reference_id="",
    timestamp_utc=None,
    source="system",
    payload=None,
):
    timestamp_utc = timestamp_utc or utc_now_iso()
    payload = payload or {}

    event_id = build_event_id(
        case_id=case_id,
        event_type=event_type,
        timestamp_utc=timestamp_utc,
        extra_text=json.dumps(payload, ensure_ascii=False, sort_keys=True),
    )

    return {
        "event_id": event_id,
        "case_id": case_id,
        "event_type": event_type,
        "timestamp_utc": timestamp_utc,
        "driver_name": driver_name,
        "load_id": load_id,
        "reference_id": reference_id,
        "source": source,
        "payload": payload,
    }


def log_dispatch_events(events, file_path=DISPATCH_EVENTS_FILE):
    if not events:
        return 0

    append_jsonl(file_path, events)
    return len(events)
