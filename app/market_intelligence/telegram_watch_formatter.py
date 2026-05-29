from app.market_intelligence.telegram_text_helpers import safe_value


HEADERS_BY_EVENT = {
    "NORMAL_STATUS_DUE": "🔎 RELOAD WATCH STATUS",
    "RELOAD_WATCH_STATUS_DUE": "🔎 RELOAD WATCH STATUS",
    "CLEAN_EXIT_FOUND": "✅ CLEAN EXIT FOUND",
    "STRONG_CHAIN_FOUND": "🔥 STRONG CHAIN FOUND",
    "PARENT_LOAD_UPDATED": "📈 WATCHED LOAD UPDATED",
    "PARENT_LOAD_REMOVED": "⚠️ WATCHED LOAD REMOVED",
    "RELOAD_WATCH_STARTED": "🟡 RELOAD WATCH STARTED",
}


def payload_value(payload, key, fallback="NEEDS CHECK"):
    return safe_value((payload or {}).get(key, ""), fallback=fallback)


def numeric_value(payload, key):
    value = (payload or {}).get(key, 0)

    if value is None or value == "":
        return 0

    return value


def money_text(value):
    if value is None or value == "":
        return "NEEDS CHECK"

    return f"${value}"


def delivery_text(payload):
    city = payload_value(payload, "delivery_city")
    state = payload_value(payload, "delivery_state")

    if city == "NEEDS CHECK" and state == "NEEDS CHECK":
        return "NEEDS CHECK"

    if state == "NEEDS CHECK":
        return city

    if city == "NEEDS CHECK":
        return state

    return f"{city}, {state}"


def counts_block(payload):
    return (
        f"Clean exits: {numeric_value(payload, 'clean_exit_count')}\n"
        f"Review exits: {numeric_value(payload, 'review_exit_count')}\n"
        f"Rate-check exits: {numeric_value(payload, 'rate_check_exit_count')}\n"
    )


def base_message(header, plan, payload):
    reason = safe_value(
        plan.get("reason", "") or payload.get("reason", ""),
        fallback="Structured reload-watch update.",
    )

    message = f"{header}\n\n"
    message += "Why shown:\n"
    message += f"{reason}\n\n"
    message += "Watched load:\n"
    message += f"Reference ID: {payload_value(payload, 'parent_reference_id')}\n"
    message += f"Delivery: {delivery_text(payload)}\n\n"

    return message


def clean_exit_block(payload):
    message = "Exit market:\n"
    message += counts_block(payload)
    message += "\nBest exit:\n"
    message += (
        f"{payload_value(payload, 'best_exit_pickup')} -> "
        f"{payload_value(payload, 'best_exit_delivery')}\n"
    )
    message += f"Rate: {money_text(payload.get('best_exit_rate'))}\n"
    message += f"Reference ID: {payload_value(payload, 'best_exit_reference_id')}\n\n"
    return message


def chain_block(payload):
    message = "Chain:\n"
    message += f"Chain status: {payload_value(payload, 'chain_status')}\n"
    message += f"Combined RPM: {money_text(payload.get('combined_rpm'))}\n"
    message += f"Market median RPM: {money_text(payload.get('market_median_rpm'))}\n\n"

    return message


def parent_update_block(payload):
    old_rate = money_text(payload.get("old_rate"))
    new_rate = money_text(payload.get("new_rate"))

    message = "Update:\n"
    message += f"Rate changed: {old_rate} -> {new_rate}\n"
    message += "Reload watch continues.\n\n"

    return message


def parent_removed_block():
    message = "Action:\n"
    message += "Reload watch should stop.\n"

    return message


def normal_status_block(payload):
    message = "Current exit context:\n"
    message += counts_block(payload)
    message += "\nAction:\n"
    message += "Continue monitoring. No Telegram buttons are attached yet.\n"

    return message


def format_reload_watch_message(plan):
    plan = plan or {}

    if plan.get("action_type") == "MUTED_NO_ACTION":
        return ""

    payload = plan.get("event_payload") or {}
    event_type = safe_value(
        plan.get("event_type") or payload.get("event_type"),
        fallback="RELOAD_WATCH_STATUS_DUE",
    )
    header = HEADERS_BY_EVENT.get(event_type, "🔎 RELOAD WATCH STATUS")

    message = base_message(header, plan, payload)

    if event_type == "CLEAN_EXIT_FOUND":
        message += clean_exit_block(payload)
    elif event_type == "STRONG_CHAIN_FOUND":
        message += chain_block(payload)
    elif event_type == "PARENT_LOAD_UPDATED":
        message += parent_update_block(payload)
    elif event_type == "PARENT_LOAD_REMOVED":
        message += parent_removed_block()
    else:
        message += normal_status_block(payload)

    return message.strip()
