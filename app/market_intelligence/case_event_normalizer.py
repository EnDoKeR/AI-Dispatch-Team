from copy import deepcopy

from app.market_intelligence.case_event_payload import (
    build_event_payload,
    json_safe,
)
from app.market_intelligence.case_event_types import (
    is_known_event_type,
    normalize_event_type,
)


WARNING_MISSING_CASE_ID = "missing_case_id"
WARNING_MISSING_TIMESTAMP_UTC = "missing_timestamp_utc"
WARNING_MISSING_SOURCE = "missing_source"
WARNING_UNKNOWN_EVENT_TYPE = "unknown_event_type"


def _event_dict(event):
    if isinstance(event, dict):
        return json_safe(deepcopy(event))

    return {}


def _text_field(event, key):
    return str(event.get(key) or "").strip()


def _warnings_for_event(event, event_type):
    warnings = []

    if not _text_field(event, "case_id"):
        warnings.append(WARNING_MISSING_CASE_ID)

    if not _text_field(event, "timestamp_utc"):
        warnings.append(WARNING_MISSING_TIMESTAMP_UTC)

    if not _text_field(event, "source"):
        warnings.append(WARNING_MISSING_SOURCE)

    if not is_known_event_type(event_type):
        warnings.append(WARNING_UNKNOWN_EVENT_TYPE)

    return warnings


def _related_ids(event):
    related = {}

    for key in [
        "event_id",
        "load_id",
        "reference_id",
        "driver_name",
    ]:
        value = event.get(key)
        if value not in (None, ""):
            related[key] = value

    return related


def _details(event):
    return {
        "legacy_event_payload": event.get("payload", {}),
    }


def normalize_case_event(event):
    legacy_payload = _event_dict(event)
    event_type = normalize_event_type(legacy_payload.get("event_type", ""))

    normalized_payload = build_event_payload(
        event_type=event_type,
        case_id=_text_field(legacy_payload, "case_id"),
        timestamp_utc=_text_field(legacy_payload, "timestamp_utc"),
        source=_text_field(legacy_payload, "source"),
        details=_details(legacy_payload),
        related_ids=_related_ids(legacy_payload),
    )

    return {
        "legacy_payload": legacy_payload,
        "normalized_payload": normalized_payload,
        "warnings": _warnings_for_event(legacy_payload, event_type),
    }
