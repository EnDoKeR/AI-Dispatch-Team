import json

from app.market_intelligence.case_event_types import (
    event_type_group,
    is_known_event_type,
    normalize_event_type,
)


BASE_EVENT_PAYLOAD_KEYS = (
    "event_type",
    "event_group",
    "case_id",
    "timestamp_utc",
    "source",
    "details",
    "related_ids",
)


def safe_event(event):
    if isinstance(event, dict):
        return dict(event)

    return {}


def sorted_keys(event):
    return sorted(str(key) for key in event.keys())


def missing_base_keys(event):
    return [
        key
        for key in BASE_EVENT_PAYLOAD_KEYS
        if key not in event
    ]


def is_json_serializable(value):
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False

    return True


def increment_count(counts, key):
    counts[key] = counts.get(key, 0) + 1


def add_unique(items, value):
    if value and value not in items:
        items.append(value)


def merge_keys(keys_by_event_type, event_type, keys):
    existing = set(keys_by_event_type.get(event_type, []))
    existing.update(keys)
    keys_by_event_type[event_type] = sorted(existing)


def merge_missing_keys(missing_by_event_type, event_type, missing_keys):
    existing = set(missing_by_event_type.get(event_type, []))
    existing.update(missing_keys)
    missing_by_event_type[event_type] = sorted(existing)


def build_case_event_builder_shape_report(events):
    safe_events = [
        safe_event(event)
        for event in events or []
    ]

    event_types = []
    keys_by_event_type = {}
    missing_base_keys_by_event_type = {}
    unknown_event_types = []
    event_group_summary = {}
    non_serializable_event_indexes = []

    for index, event in enumerate(safe_events):
        event_type = normalize_event_type(event.get("event_type", ""))
        group = event_type_group(event_type)

        add_unique(event_types, event_type)
        merge_keys(keys_by_event_type, event_type, sorted_keys(event))
        merge_missing_keys(
            missing_base_keys_by_event_type,
            event_type,
            missing_base_keys(event),
        )
        increment_count(event_group_summary, group)

        if not is_known_event_type(event_type):
            add_unique(unknown_event_types, event_type)

        if not is_json_serializable(event):
            non_serializable_event_indexes.append(index)

    return {
        "total_events": len(safe_events),
        "event_types": sorted(event_types),
        "keys_by_event_type": dict(sorted(keys_by_event_type.items())),
        "missing_base_keys_by_event_type": dict(
            sorted(missing_base_keys_by_event_type.items())
        ),
        "unknown_event_types": unknown_event_types,
        "event_group_summary": dict(sorted(event_group_summary.items())),
        "json_serializable": not non_serializable_event_indexes,
        "non_serializable_event_indexes": non_serializable_event_indexes,
    }
