from app.market_intelligence.market_baseline import to_number
from app.market_intelligence.market_zone_snapshot import (
    city_from_key,
    city_state_key,
    state_from_key,
)


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


def event_name(event_type):
    return str(event_type or "").strip().upper()


def delivery_city_state(parent_load, watch_state):
    delivery = safe_get(parent_load, "delivery", "")
    city = safe_get(watch_state, "delivery_city", "")
    state = safe_get(watch_state, "delivery_state", "")

    if city and state:
        return text_value(city), text_value(state)

    if not delivery:
        return text_value(city), text_value(state)

    key = city_state_key(delivery)

    return city_from_key(key), state_from_key(key)


def build_reload_watch_event_payload(
    event_type,
    watch_state=None,
    parent_load=None,
    exit_context=None,
    best_exit_load=None,
    chain_result=None,
    rate_update=None,
    source="reload_watch_state",
    reason="",
):
    watch_state = watch_state or {}
    exit_context = exit_context or {}
    chain_result = chain_result or {}
    rate_update = rate_update or {}
    delivery_city, delivery_state = delivery_city_state(parent_load, watch_state)

    return {
        "watch_id": text_value(safe_get(watch_state, "watch_id", "")),
        "parent_load_id": text_value(
            safe_get(
                watch_state,
                "parent_load_id",
                safe_get(parent_load, "load_id", ""),
            )
        ),
        "parent_reference_id": text_value(
            safe_get(
                watch_state,
                "parent_reference_id",
                safe_get(parent_load, "reference_id", ""),
            )
        ),
        "driver_name": text_value(
            safe_get(
                watch_state,
                "driver_name",
                safe_get(parent_load, "driver_name", ""),
            )
        ),
        "delivery_city": delivery_city,
        "delivery_state": delivery_state,
        "watch_status": text_value(
            safe_get(watch_state, "watch_status", "")
        ),
        "event_type": event_name(event_type),
        "reason": text_value(reason),
        "clean_exit_count": int(numeric_value(
            safe_get(exit_context, "clean_exit_count", 0)
        )),
        "review_exit_count": int(numeric_value(
            safe_get(exit_context, "review_exit_count", 0)
        )),
        "rate_check_exit_count": int(numeric_value(
            safe_get(exit_context, "rate_check_exit_count", 0)
        )),
        "best_exit_reference_id": text_value(
            safe_get(best_exit_load, "reference_id", "")
        ),
        "best_exit_pickup": text_value(
            safe_get(best_exit_load, "pickup", "")
        ),
        "best_exit_delivery": text_value(
            safe_get(best_exit_load, "delivery", "")
        ),
        "best_exit_rate": numeric_value(
            safe_get(best_exit_load, "rate", 0)
        ),
        "chain_status": text_value(
            safe_get(chain_result, "chain_status", "")
        ),
        "combined_rpm": numeric_value(
            safe_get(chain_result, "combined_rpm", 0)
        ),
        "market_median_rpm": numeric_value(
            safe_get(chain_result, "market_median_rpm", 0)
        ),
        "old_rate": numeric_value(safe_get(rate_update, "old_rate", 0)),
        "new_rate": numeric_value(safe_get(rate_update, "new_rate", 0)),
        "source": text_value(source),
    }
