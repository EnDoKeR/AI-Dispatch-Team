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

    event_type = normalize_event_type(record.get("event_type", ""))

    record["event_type"] = event_type
    record["event_group"] = event_type_group(event_type)
    record["case_id"] = str(record.get("case_id", "") or "").strip()
    record["timestamp_utc"] = str(record.get("timestamp_utc", "") or "").strip()
    record["source"] = str(record.get("source", "") or "").strip()

    return record


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

    for event in safe_events:
        event_type = event.get("event_type", "")
        event_group = event.get("event_group", "")
        case_id = event.get("case_id", "")

        increment_count(counts_by_event_type, event_type)
        increment_count(counts_by_event_group, event_group)
        increment_count(counts_by_case_id, case_id)

        if not is_known_event_type(event_type):
            add_unique(unknown_event_types, event_type)

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
        "timeline_by_case_id": dict(sorted(timeline_by_case_id.items())),
    }
