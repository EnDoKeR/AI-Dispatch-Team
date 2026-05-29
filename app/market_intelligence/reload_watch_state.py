TERMINAL_STATUSES = [
    "WATCH_STOPPED",
    "DRIVER_LOADED",
    "PARENT_LOAD_REMOVED",
]


STOP_EVENTS = {
    "DRIVER_LOADED": ("DRIVER_LOADED", "Driver is loaded; reload watch should stop."),
    "STOP_SEARCH": ("WATCH_STOPPED", "Dispatcher stopped search; reload watch should stop."),
    "WATCH_STOPPED": ("WATCH_STOPPED", "Reload watch was stopped."),
}


CRITICAL_CONTINUE_EVENTS = {
    "PARENT_LOAD_UPDATED": "Parent load changed; notify dispatcher and continue watching.",
    "CLEAN_EXIT_FOUND": "Clean exit appeared; notify dispatcher and continue watching.",
    "STRONG_CHAIN_FOUND": "Strong two-load chain appeared; notify dispatcher and continue watching.",
}


def normalize_event_type(event_type):
    return str(event_type or "PARENT_LOAD_ACTIVE").strip().upper()


def current_watch_status(watch_state):
    return str(
        (watch_state or {}).get("watch_status", "WATCH_ACTIVE")
        or "WATCH_ACTIVE"
    ).strip().upper()


def normal_updates_are_muted(watch_state):
    state = watch_state or {}
    status = current_watch_status(state)

    return bool(state.get("mute_normal_updates", False)) or status == "WATCH_MUTED"


def base_decision(watch_state):
    muted = normal_updates_are_muted(watch_state)

    return {
        "watch_status": "WATCH_MUTED" if muted else "WATCH_ACTIVE",
        "continue_watch": True,
        "stop_watch": False,
        "send_normal_status": False,
        "send_critical_alert": False,
        "mute_normal_updates": muted,
        "reason": "Reload watch remains active.",
    }


def stop_decision(status, reason, critical_alert=False):
    return {
        "watch_status": status,
        "continue_watch": False,
        "stop_watch": True,
        "send_normal_status": False,
        "send_critical_alert": critical_alert,
        "mute_normal_updates": False,
        "reason": reason,
    }


def continue_with_critical_decision(watch_state, status, reason):
    decision = base_decision(watch_state)
    decision.update(
        {
            "watch_status": status,
            "send_normal_status": False,
            "send_critical_alert": True,
            "reason": reason,
        }
    )

    return decision


def evaluate_reload_watch_state(watch_state=None, event_type="PARENT_LOAD_ACTIVE"):
    event_type = normalize_event_type(event_type)
    status = current_watch_status(watch_state)

    if status in TERMINAL_STATUSES and event_type == "PARENT_LOAD_ACTIVE":
        return stop_decision(
            status,
            "Reload watch is already stopped or closed.",
            critical_alert=False,
        )

    if event_type in STOP_EVENTS:
        stop_status, reason = STOP_EVENTS[event_type]
        return stop_decision(stop_status, reason)

    if event_type == "PARENT_LOAD_REMOVED":
        return stop_decision(
            "PARENT_LOAD_REMOVED",
            "Parent load was removed; notify dispatcher and stop reload watch.",
            critical_alert=True,
        )

    if event_type == "MUTE_WATCH_UPDATES":
        decision = base_decision(
            {
                **(watch_state or {}),
                "watch_status": "WATCH_MUTED",
                "mute_normal_updates": True,
            }
        )
        decision["reason"] = "Normal reload-watch updates are muted."
        return decision

    if event_type == "NORMAL_STATUS_DUE":
        decision = base_decision(watch_state)
        decision["send_normal_status"] = not decision["mute_normal_updates"]
        decision["reason"] = (
            "Normal reload-watch status is due."
            if decision["send_normal_status"]
            else "Normal reload-watch status is muted."
        )
        return decision

    if event_type in CRITICAL_CONTINUE_EVENTS:
        return continue_with_critical_decision(
            watch_state,
            event_type,
            CRITICAL_CONTINUE_EVENTS[event_type],
        )

    return base_decision(watch_state)
