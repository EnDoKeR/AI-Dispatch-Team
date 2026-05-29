from app.market_intelligence.reload_watch_event_builder import (
    build_reload_watch_event_payload,
)
from app.market_intelligence.reload_watch_state import (
    evaluate_reload_watch_state,
    normalize_event_type,
)


def choose_action_type(decision, event_type):
    if decision["send_critical_alert"]:
        return "CRITICAL_ALERT"

    if decision["send_normal_status"]:
        return "NORMAL_STATUS"

    if decision["stop_watch"]:
        return "STOP_WATCH"

    if event_type == "NORMAL_STATUS_DUE" and decision["mute_normal_updates"]:
        return "MUTED_NO_ACTION"

    return "NO_ACTION"


def plan_reload_watch_action(
    watch_state=None,
    event_type="PARENT_LOAD_ACTIVE",
    parent_load=None,
    exit_context=None,
    best_exit_load=None,
    chain_result=None,
    rate_update=None,
    source="reload_watch_action_planner",
):
    normalized_event_type = normalize_event_type(event_type)
    decision = evaluate_reload_watch_state(
        watch_state=watch_state,
        event_type=normalized_event_type,
    )
    event_payload = build_reload_watch_event_payload(
        event_type=normalized_event_type,
        watch_state=watch_state,
        parent_load=parent_load,
        exit_context=exit_context,
        best_exit_load=best_exit_load,
        chain_result=chain_result,
        rate_update=rate_update,
        source=source,
        reason=decision["reason"],
    )

    return {
        "watch_status": decision["watch_status"],
        "continue_watch": decision["continue_watch"],
        "stop_watch": decision["stop_watch"],
        "send_normal_status": decision["send_normal_status"],
        "send_critical_alert": decision["send_critical_alert"],
        "event_type": normalized_event_type,
        "event_payload": event_payload,
        "action_type": choose_action_type(decision, normalized_event_type),
        "reason": decision["reason"],
    }
