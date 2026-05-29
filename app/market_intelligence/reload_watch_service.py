from app.market_intelligence.reload_watch_action_planner import (
    plan_reload_watch_action,
)
from app.market_intelligence.reload_watch_record import (
    build_reload_watch_record,
    update_reload_watch_record,
)
from app.market_intelligence.reload_watch_repository import (
    RELOAD_WATCH_FILE,
    get_reload_watch_by_id,
    upsert_reload_watch_record,
)


def success_result(watch_record, action_plan=None, reason="", saved=True):
    return {
        "watch_record": watch_record,
        "action_plan": action_plan or {},
        "saved": saved,
        "reason": reason,
    }


def failure_result(reason):
    return {
        "watch_record": None,
        "action_plan": {},
        "saved": False,
        "reason": reason,
    }


def start_reload_watch(
    watch_id,
    parent_load=None,
    payload=None,
    timestamp_utc="",
    file_path=RELOAD_WATCH_FILE,
):
    if not str(watch_id or "").strip():
        return failure_result("Missing watch_id; reload watch was not started.")

    watch_record = build_reload_watch_record(
        watch_id=watch_id,
        parent_load=parent_load,
        payload=payload,
        timestamp_utc=timestamp_utc,
    )
    saved_record = upsert_reload_watch_record(watch_record, file_path)

    return success_result(
        saved_record,
        reason="Reload watch started.",
        saved=True,
    )


def handle_reload_watch_event(
    watch_id,
    event_type,
    parent_load=None,
    exit_context=None,
    best_exit_load=None,
    chain_result=None,
    rate_update=None,
    timestamp_utc="",
    file_path=RELOAD_WATCH_FILE,
):
    if not str(watch_id or "").strip():
        return failure_result("Missing watch_id; reload watch event was not handled.")

    watch_record = get_reload_watch_by_id(watch_id, file_path)

    if watch_record is None:
        return failure_result("Reload watch was not found.")

    action_plan = plan_reload_watch_action(
        watch_state=watch_record,
        event_type=event_type,
        parent_load=parent_load,
        exit_context=exit_context,
        best_exit_load=best_exit_load,
        chain_result=chain_result,
        rate_update=rate_update,
        source="reload_watch_service",
    )
    updated_record = update_reload_watch_record(
        watch_record,
        action_plan=action_plan,
        timestamp_utc=timestamp_utc,
    )
    saved_record = upsert_reload_watch_record(updated_record, file_path)

    return success_result(
        saved_record,
        action_plan=action_plan,
        reason=action_plan.get("reason", ""),
        saved=True,
    )
