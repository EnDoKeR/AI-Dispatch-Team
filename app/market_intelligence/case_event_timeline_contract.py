"""Pure Event Timeline contract helpers for dispatch workflow reports."""

from copy import deepcopy

from app.market_intelligence.case_event_types import (
    event_type_group,
    is_known_event_type,
    normalize_event_type,
)


TIMELINE_SCHEMA_VERSION = "timeline_event_v1"


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


def normalize_dict(value):
    if isinstance(value, dict):
        return json_safe(deepcopy(value))

    return {}


def normalize_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        items = deepcopy(value)
    elif isinstance(value, (tuple, set)):
        items = list(value)
    elif isinstance(value, str):
        items = [value]
    else:
        items = [value]

    return [
        json_safe(item)
        for item in items
        if item not in ["", None]
    ]


def build_timeline_event(
    event_type,
    case_id="",
    event_id="",
    created_at="",
    actor_type="system",
    actor_id="",
    payload=None,
    evidence_refs=None,
    source="",
    idempotency_key="",
    schema_version=TIMELINE_SCHEMA_VERSION,
):
    normalized_event_type = normalize_event_type(event_type)

    return {
        "event_id": str(event_id or "").strip(),
        "case_id": str(case_id or "").strip(),
        "event_type": normalized_event_type,
        "event_group": event_type_group(normalized_event_type),
        "known_event_type": is_known_event_type(normalized_event_type),
        "created_at": str(created_at or "").strip(),
        "actor_type": str(actor_type or "system").strip(),
        "actor_id": str(actor_id or "").strip(),
        "payload": normalize_dict(payload),
        "evidence_refs": normalize_list(evidence_refs),
        "source": str(source or "").strip(),
        "idempotency_key": str(idempotency_key or "").strip(),
        "schema_version": str(schema_version or TIMELINE_SCHEMA_VERSION).strip(),
    }


def safe_timeline_event(event):
    if not isinstance(event, dict):
        return build_timeline_event("")

    return build_timeline_event(
        event_type=event.get("event_type", ""),
        case_id=event.get("case_id", ""),
        event_id=event.get("event_id", ""),
        created_at=event.get("created_at", event.get("timestamp_utc", "")),
        actor_type=event.get("actor_type", "system"),
        actor_id=event.get("actor_id", ""),
        payload=event.get("payload", event.get("details", {})),
        evidence_refs=event.get("evidence_refs", []),
        source=event.get("source", ""),
        idempotency_key=event.get("idempotency_key", ""),
        schema_version=event.get("schema_version", TIMELINE_SCHEMA_VERSION),
    )


def append_timeline_event(events, event):
    safe_events = [
        json_safe(deepcopy(item))
        for item in events or []
        if isinstance(item, dict)
    ]
    normalized_event = safe_timeline_event(event)
    idempotency_key = normalized_event.get("idempotency_key", "")

    if idempotency_key:
        for existing_event in safe_events:
            if str(existing_event.get("idempotency_key", "") or "") == idempotency_key:
                return safe_events

    return safe_events + [normalized_event]


def sort_timeline_events(events):
    safe_events = [
        json_safe(deepcopy(item))
        for item in events or []
        if isinstance(item, dict)
    ]

    return sorted(
        safe_events,
        key=lambda event: (
            str(event.get("created_at", "") or ""),
            str(event.get("event_id", "") or ""),
        ),
    )
