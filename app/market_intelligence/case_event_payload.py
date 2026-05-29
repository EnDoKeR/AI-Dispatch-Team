from copy import deepcopy

from app.market_intelligence.case_event_types import (
    event_type_group,
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


def normalize_dict(value):
    if isinstance(value, dict):
        return json_safe(deepcopy(value))

    return {}


def build_event_payload(
    event_type,
    case_id="",
    timestamp_utc="",
    source="",
    details=None,
    related_ids=None,
):
    normalized_event_type = normalize_event_type(event_type)

    return {
        "event_type": normalized_event_type,
        "event_group": event_type_group(normalized_event_type),
        "case_id": str(case_id or "").strip(),
        "timestamp_utc": str(timestamp_utc or "").strip(),
        "source": str(source or "").strip(),
        "details": normalize_dict(details),
        "related_ids": normalize_dict(related_ids),
    }
