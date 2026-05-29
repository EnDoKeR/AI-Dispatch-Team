from copy import deepcopy

from app.market_intelligence.market_baseline import to_number
from app.market_intelligence.market_zone_snapshot import (
    city_from_key,
    city_state_key,
    state_from_key,
)


SUMMARY_FIELDS = [
    "clean_exit_count",
    "review_exit_count",
    "rate_check_exit_count",
    "best_exit_reference_id",
    "best_exit_pickup",
    "best_exit_delivery",
    "best_exit_rate",
    "chain_status",
    "combined_rpm",
    "market_median_rpm",
]


TEXT_FIELDS = [
    "watch_id",
    "watch_status",
    "parent_load_id",
    "parent_reference_id",
    "driver_name",
    "delivery_city",
    "delivery_state",
    "started_at_utc",
    "updated_at_utc",
    "last_checked_at_utc",
    "last_event_type",
    "best_exit_reference_id",
    "best_exit_pickup",
    "best_exit_delivery",
    "chain_status",
]


NUMERIC_FIELDS = [
    "clean_exit_count",
    "review_exit_count",
    "rate_check_exit_count",
    "best_exit_rate",
    "combined_rpm",
    "market_median_rpm",
]


TERMINAL_EVENT_STATUS = {
    "DRIVER_LOADED": "DRIVER_LOADED",
    "STOP_SEARCH": "WATCH_STOPPED",
    "WATCH_STOPPED": "WATCH_STOPPED",
    "PARENT_LOAD_REMOVED": "PARENT_LOAD_REMOVED",
}


def safe_get(record, key, default=""):
    if record is None:
        return default

    if isinstance(record, dict):
        return record.get(key, default)

    return getattr(record, key, default)


def text_value(value):
    if value is None:
        return ""

    return str(value)


def numeric_value(value):
    return to_number(value)


def event_name(value):
    return str(value or "").strip().upper()


def delivery_city_state(parent_load, payload):
    city = safe_get(payload, "delivery_city", "")
    state = safe_get(payload, "delivery_state", "")

    if city or state:
        return text_value(city), text_value(state)

    delivery = safe_get(parent_load, "delivery", "")

    if not delivery:
        return "", ""

    key = city_state_key(delivery)

    return city_from_key(key), state_from_key(key)


def default_record():
    return {
        "watch_id": "",
        "watch_status": "WATCH_ACTIVE",
        "parent_load_id": "",
        "parent_reference_id": "",
        "driver_name": "",
        "delivery_city": "",
        "delivery_state": "",
        "mute_normal_updates": False,
        "started_at_utc": "",
        "updated_at_utc": "",
        "last_checked_at_utc": "",
        "last_event_type": "",
        "last_event_payload": {},
        "clean_exit_count": 0,
        "review_exit_count": 0,
        "rate_check_exit_count": 0,
        "best_exit_reference_id": "",
        "best_exit_pickup": "",
        "best_exit_delivery": "",
        "best_exit_rate": 0,
        "chain_status": "",
        "combined_rpm": 0,
        "market_median_rpm": 0,
    }


def normalize_record(record):
    normalized = dict(default_record())
    normalized.update(record or {})

    for field in TEXT_FIELDS:
        normalized[field] = text_value(normalized.get(field, ""))

    for field in NUMERIC_FIELDS:
        normalized[field] = numeric_value(normalized.get(field, 0))

    normalized["mute_normal_updates"] = bool(
        normalized.get("mute_normal_updates", False)
    )
    normalized["last_event_payload"] = dict(
        normalized.get("last_event_payload") or {}
    )

    return normalized


def apply_summary_fields(record, payload):
    for field in SUMMARY_FIELDS:
        if field not in payload:
            continue

        if field in NUMERIC_FIELDS:
            record[field] = numeric_value(payload.get(field, 0))
        else:
            record[field] = text_value(payload.get(field, ""))

    return record


def build_reload_watch_record(
    watch_id="",
    parent_load=None,
    payload=None,
    timestamp_utc="",
):
    payload = payload or {}
    delivery_city, delivery_state = delivery_city_state(parent_load, payload)

    record = default_record()
    record.update(
        {
            "watch_id": text_value(watch_id or safe_get(payload, "watch_id", "")),
            "watch_status": "WATCH_ACTIVE",
            "parent_load_id": text_value(
                safe_get(
                    payload,
                    "parent_load_id",
                    safe_get(parent_load, "load_id", ""),
                )
            ),
            "parent_reference_id": text_value(
                safe_get(
                    payload,
                    "parent_reference_id",
                    safe_get(parent_load, "reference_id", ""),
                )
            ),
            "driver_name": text_value(
                safe_get(
                    payload,
                    "driver_name",
                    safe_get(parent_load, "driver_name", ""),
                )
            ),
            "delivery_city": delivery_city,
            "delivery_state": delivery_state,
            "started_at_utc": text_value(timestamp_utc),
            "updated_at_utc": text_value(timestamp_utc),
            "last_checked_at_utc": text_value(timestamp_utc),
        }
    )
    apply_summary_fields(record, payload)

    return normalize_record(record)


def event_status(record, event_type):
    current_status = event_name(record.get("watch_status", "WATCH_ACTIVE"))

    if event_type in TERMINAL_EVENT_STATUS:
        return TERMINAL_EVENT_STATUS[event_type]

    if event_type == "MUTE_WATCH_UPDATES":
        return "WATCH_MUTED"

    if current_status == "WATCH_MUTED":
        return "WATCH_MUTED"

    return "WATCH_ACTIVE"


def update_reload_watch_record(record, action_plan=None, timestamp_utc=""):
    updated = normalize_record(deepcopy(record or {}))
    plan = deepcopy(action_plan or {})
    payload = dict(plan.get("event_payload") or {})
    event_type = event_name(
        plan.get("event_type") or payload.get("event_type") or ""
    )

    updated["watch_status"] = event_status(updated, event_type)
    updated["mute_normal_updates"] = (
        event_type == "MUTE_WATCH_UPDATES"
        or updated["watch_status"] == "WATCH_MUTED"
    )
    if timestamp_utc:
        updated["updated_at_utc"] = text_value(timestamp_utc)
        updated["last_checked_at_utc"] = text_value(timestamp_utc)

    updated["last_event_type"] = event_type
    updated["last_event_payload"] = payload
    apply_summary_fields(updated, payload)

    return normalize_record(updated)
