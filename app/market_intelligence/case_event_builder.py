from app.market_intelligence.event_logger import build_dispatch_event


def build_ai_decision_created_event(case_id, case_record, decision_record):
    return build_dispatch_event(
        case_id=case_id,
        event_type="AI_DECISION_CREATED",
        driver_name=case_record.get("driver_name", ""),
        load_id=case_record.get("load_id", ""),
        reference_id=case_record.get("reference_id", ""),
        timestamp_utc=decision_record.get("timestamp_utc", ""),
        source="decision_logger",
        payload={
            "decision": decision_record.get("decision", ""),
            "category": decision_record.get("category", ""),
            "score": decision_record.get("score", 0),
            "reasons": decision_record.get("reasons", []),
            "pickup": decision_record.get("pickup", ""),
            "delivery": decision_record.get("delivery", ""),
            "rate": decision_record.get("rate", 0),
        },
    )


def build_telegram_alert_sent_event(case_id, case_record, outbox_record):
    return build_dispatch_event(
        case_id=case_id,
        event_type="TELEGRAM_ALERT_SENT",
        driver_name=case_record.get("driver_name", ""),
        load_id=case_record.get("load_id", ""),
        reference_id=case_record.get("reference_id", ""),
        timestamp_utc=outbox_record.get("timestamp_utc", ""),
        source="telegram_outbox",
        payload={
            "message_type": outbox_record.get("message_type", ""),
            "category": outbox_record.get("category", ""),
            "telegram_message_id": outbox_record.get("telegram_message_id", ""),
            "pickup": outbox_record.get("pickup", ""),
            "delivery": outbox_record.get("delivery", ""),
            "rate": outbox_record.get("rate", ""),
            "broker": outbox_record.get("broker", ""),
            "broker_mc": outbox_record.get("broker_mc", ""),
            "reference_id": outbox_record.get("reference_id", ""),
        },
    )


def build_simulation_event_payload(simulation_event):
    payload = simulation_event.get("payload", {}) or {}
    event_type = simulation_event.get("event_type", "")
    event_load = payload.get("load", {}) or {}
    updates = payload.get("updates", {}) or {}

    if event_type == "LOAD_APPEARED":
        return {
            "simulation_step": simulation_event.get("simulation_step", ""),
            "event_time": simulation_event.get("event_time", ""),
            "simulation_load_id": simulation_event.get("load_id", ""),
            "pickup": event_load.get("pickup", ""),
            "delivery": event_load.get("delivery", ""),
            "rate": event_load.get("rate", ""),
            "broker": event_load.get("broker_name", ""),
            "broker_mc": event_load.get("broker_mc", ""),
            "reference_id": event_load.get(
                "reference_id",
                simulation_event.get("load_id", ""),
            ),
        }

    if event_type == "LOAD_UPDATED":
        return {
            "simulation_step": simulation_event.get("simulation_step", ""),
            "event_time": simulation_event.get("event_time", ""),
            "simulation_load_id": simulation_event.get("load_id", ""),
            "updates": updates,
        }

    if event_type == "LOAD_REMOVED":
        return {
            "simulation_step": simulation_event.get("simulation_step", ""),
            "event_time": simulation_event.get("event_time", ""),
            "simulation_load_id": simulation_event.get("load_id", ""),
            "reason": simulation_event.get("reason", ""),
        }

    return {
        "simulation_step": simulation_event.get("simulation_step", ""),
        "event_time": simulation_event.get("event_time", ""),
        "simulation_load_id": simulation_event.get("load_id", ""),
        "payload": payload,
    }


def build_load_board_simulation_event(case_id, case_record, simulation_event):
    return build_dispatch_event(
        case_id=case_id,
        event_type=simulation_event.get("event_type", ""),
        driver_name=case_record.get("driver_name", ""),
        load_id=case_record.get("load_id", ""),
        reference_id=case_record.get("reference_id", ""),
        timestamp_utc=simulation_event.get("timestamp_utc", ""),
        source="load_board_simulation",
        payload=build_simulation_event_payload(simulation_event),
    )


def build_dispatcher_feedback_added_event(case_id, case_record, feedback_record):
    return build_dispatch_event(
        case_id=case_id,
        event_type="DISPATCHER_FEEDBACK_ADDED",
        driver_name=case_record.get("driver_name", ""),
        load_id=case_record.get("load_id", ""),
        reference_id=case_record.get("reference_id", ""),
        timestamp_utc=feedback_record.get("timestamp_utc", ""),
        source=feedback_record.get("source", "dispatcher_feedback"),
        payload={
            "feedback": feedback_record.get("dispatcher_feedback", ""),
            "note": feedback_record.get("dispatcher_note", ""),
            "document_path": feedback_record.get("document_path", ""),
        },
    )


def build_ratecon_received_event(case_id, case_record, feedback_record):
    return build_dispatch_event(
        case_id=case_id,
        event_type="RATECON_RECEIVED",
        driver_name=case_record.get("driver_name", ""),
        load_id=case_record.get("load_id", ""),
        reference_id=case_record.get("reference_id", ""),
        timestamp_utc=feedback_record.get("timestamp_utc", ""),
        source=feedback_record.get("source", "telegram_document"),
        payload={
            "document_path": feedback_record.get("document_path", ""),
            "note": feedback_record.get("dispatcher_note", ""),
        },
    )


def dedupe_dispatch_events(events):
    deduped_events = []
    seen_event_keys = set()

    for event in events:
        payload = event.get("payload", {}) or {}

        event_key = "|".join(
            [
                str(event.get("case_id", "")),
                str(event.get("event_type", "")),
                str(event.get("timestamp_utc", "")),
                str(event.get("source", "")),
                str(payload.get("simulation_step", "")),
                str(payload.get("simulation_load_id", "")),
                str(payload.get("telegram_message_id", "")),
                str(payload.get("feedback", "")),
                str(payload.get("document_path", "")),
            ]
        )

        if event_key in seen_event_keys:
            continue

        seen_event_keys.add(event_key)
        deduped_events.append(event)

    return deduped_events
