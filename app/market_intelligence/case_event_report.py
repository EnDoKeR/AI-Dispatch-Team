from copy import deepcopy

from app.market_intelligence.case_event_types import (
    event_type_group,
    is_known_event_type,
    normalize_event_type,
)


def json_safe(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    return str(value)


def safe_event_record(event):
    if isinstance(event, dict):
        record = json_safe(deepcopy(event))
    else:
        record = {}

    if is_wrapper_event_record(record):
        return safe_wrapper_event_record(record)

    event_type = normalize_event_type(record.get("event_type", ""))

    record["event_type"] = event_type
    record["event_group"] = event_type_group(event_type)
    record["case_id"] = str(record.get("case_id", "") or "").strip()
    record["timestamp_utc"] = str(record.get("timestamp_utc", "") or "").strip()
    record["source"] = str(record.get("source", "") or "").strip()
    record["warnings"] = []

    return record


def is_wrapper_event_record(record):
    return (
        isinstance(record, dict)
        and isinstance(record.get("normalized_payload"), dict)
        and "legacy_payload" in record
    )


def safe_list(value):
    if isinstance(value, list):
        return json_safe(deepcopy(value))

    return []


def safe_wrapper_event_record(record):
    normalized = record.get("normalized_payload") or {}
    event_type = normalize_event_type(normalized.get("event_type", ""))
    event_group = str(
        normalized.get("event_group")
        or event_type_group(event_type)
        or ""
    ).strip()

    return {
        "event_type": event_type,
        "event_group": event_group,
        "case_id": str(normalized.get("case_id", "") or "").strip(),
        "timestamp_utc": str(normalized.get("timestamp_utc", "") or "").strip(),
        "source": str(normalized.get("source", "") or "").strip(),
        "details": json_safe(deepcopy(normalized.get("details") or {})),
        "related_ids": json_safe(deepcopy(normalized.get("related_ids") or {})),
        "legacy_payload": json_safe(deepcopy(record.get("legacy_payload") or {})),
        "warnings": safe_list(record.get("warnings")),
    }


def increment_count(counts, key):
    counts[key] = counts.get(key, 0) + 1


def add_unique(items, value):
    if value and value not in items:
        items.append(value)


def newer_event(candidate, current):
    if not current:
        return True

    candidate_timestamp = candidate.get("timestamp_utc", "")
    current_timestamp = current.get("timestamp_utc", "")

    if not current_timestamp:
        return True

    if not candidate_timestamp:
        return False

    return candidate_timestamp >= current_timestamp


def build_case_event_report(events):
    safe_events = [
        safe_event_record(event)
        for event in events or []
    ]

    counts_by_event_type = {}
    counts_by_event_group = {}
    counts_by_case_id = {}
    latest_event_by_case_id = {}
    timeline_by_case_id = {}
    unknown_event_types = []
    warnings_by_type = {}

    for event in safe_events:
        event_type = event.get("event_type", "")
        event_group = event.get("event_group", "")
        case_id = event.get("case_id", "")

        increment_count(counts_by_event_type, event_type)
        increment_count(counts_by_event_group, event_group)
        increment_count(counts_by_case_id, case_id)

        if not is_known_event_type(event_type):
            add_unique(unknown_event_types, event_type)

        for warning in event.get("warnings", []):
            increment_count(warnings_by_type, warning)

        timeline_by_case_id.setdefault(case_id, []).append(event)

        if newer_event(event, latest_event_by_case_id.get(case_id)):
            latest_event_by_case_id[case_id] = event

    return {
        "total_events": len(safe_events),
        "counts_by_event_type": dict(sorted(counts_by_event_type.items())),
        "counts_by_event_group": dict(sorted(counts_by_event_group.items())),
        "counts_by_case_id": dict(sorted(counts_by_case_id.items())),
        "latest_event_by_case_id": dict(sorted(latest_event_by_case_id.items())),
        "unknown_event_types": unknown_event_types,
        "warnings_count": sum(warnings_by_type.values()),
        "warnings_by_type": dict(sorted(warnings_by_type.items())),
        "timeline_by_case_id": dict(sorted(timeline_by_case_id.items())),
    }
