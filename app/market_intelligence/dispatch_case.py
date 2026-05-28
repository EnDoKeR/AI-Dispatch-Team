import json
from app.market_intelligence.case_id_resolver import (
    build_case_id,
    normalize_text,
    stable_hash,
)
from pathlib import Path
from app.market_intelligence.case_status_engine import (
    apply_status_update_to_case,
    status_from_feedback,
    status_update_from_feedback,
    status_update_from_simulation_removed,
)
from app.market_intelligence.case_event_builder import (
    build_ai_decision_created_event,
    build_dispatcher_feedback_added_event,
    build_load_board_simulation_event,
    build_ratecon_received_event,
    build_telegram_alert_sent_event,
    dedupe_dispatch_events,
)


DISPATCH_CASES_FILE = Path("data/dispatch_cases.jsonl")




def safe(value, default=""):
    if value is None:
        return default

    return value


def load_jsonl(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        return []

    records = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records


def write_jsonl(file_path, records):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


# Case ID helpers are implemented in:
# app.market_intelligence.case_id_resolver


# Status rules are implemented in:
# app.market_intelligence.case_status_engine


def build_case_from_decision(decision_record):
    case_id = build_case_id(
        driver_name=decision_record.get("driver_name", ""),
        load_id=decision_record.get("load_id", ""),
        reference_id=decision_record.get("reference_id", ""),
        broker_mc=decision_record.get("broker_mc", ""),
    )

    return {
        "case_id": case_id,
        "created_at_utc": decision_record.get("timestamp_utc", ""),
        "updated_at_utc": decision_record.get("timestamp_utc", ""),

        "status": "OPEN",
        "final_outcome": None,

        "driver_name": safe(decision_record.get("driver_name", "")),
        "driver_location": safe(decision_record.get("driver_location", "")),
        "driver_equipment": safe(decision_record.get("driver_equipment", "")),

        "load_id": safe(decision_record.get("load_id", "")),
        "reference_id": safe(decision_record.get("reference_id", "")),

        "pickup": safe(decision_record.get("pickup", "")),
        "delivery": safe(decision_record.get("delivery", "")),
        "rate": safe(decision_record.get("rate", 0)),
        "loaded_miles": safe(decision_record.get("loaded_miles", 0)),
        "empty_miles": safe(decision_record.get("empty_miles", 0)),
        "total_miles": safe(decision_record.get("total_miles", 0)),
        "total_rpm": safe(decision_record.get("total_rpm", 0)),
        "weight": safe(decision_record.get("weight", 0)),
        "posted_trailer_type": safe(decision_record.get("posted_trailer_type", "")),
        "commodity": safe(decision_record.get("commodity", "")),

        "broker_name": safe(decision_record.get("broker_name", "")),
        "broker_mc": safe(decision_record.get("broker_mc", "")),
        "broker_contact": safe(decision_record.get("broker_contact", "")),
        "broker_status": safe(decision_record.get("broker_status", "")),
        "credit_score": safe(decision_record.get("credit_score", "")),
        "days_to_pay": safe(decision_record.get("days_to_pay", "")),

        "ai_decision": {
            "decision": safe(decision_record.get("decision", "")),
            "category": safe(decision_record.get("category", "")),
            "score": safe(decision_record.get("score", 0)),
            "priority": safe(decision_record.get("priority", "")),
            "suggested_action": safe(decision_record.get("suggested_action", "")),
            "reasons": decision_record.get("reasons", []),
            "timestamp_utc": decision_record.get("timestamp_utc", ""),
        },

        "telegram_alerts": [],
        "dispatcher_feedback": [],
        "ratecons": [],
        "events_count": 0,
    }


def build_case_from_outbox(outbox_record):
    case_id = build_case_id(
        driver_name=outbox_record.get("driver_name", ""),
        load_id="",
        reference_id=outbox_record.get("reference_id", ""),
        broker_mc=outbox_record.get("broker_mc", ""),
    )

    return {
        "case_id": case_id,
        "created_at_utc": outbox_record.get("timestamp_utc", ""),
        "updated_at_utc": outbox_record.get("timestamp_utc", ""),

        "status": "OPEN",
        "final_outcome": None,

        "driver_name": safe(outbox_record.get("driver_name", "")),
        "driver_location": "",
        "driver_equipment": "",

        "load_id": "",
        "reference_id": safe(outbox_record.get("reference_id", "")),

        "pickup": safe(outbox_record.get("pickup", "")),
        "delivery": safe(outbox_record.get("delivery", "")),
        "rate": safe(outbox_record.get("rate", "")),
        "loaded_miles": 0,
        "empty_miles": 0,
        "total_miles": 0,
        "total_rpm": 0,
        "weight": 0,
        "posted_trailer_type": "",
        "commodity": "",

        "broker_name": safe(outbox_record.get("broker", "")),
        "broker_mc": safe(outbox_record.get("broker_mc", "")),
        "broker_contact": "",
        "broker_status": "",
        "credit_score": "",
        "days_to_pay": "",

        "ai_decision": {
            "decision": "",
            "category": safe(outbox_record.get("category", "")),
            "score": 0,
            "priority": "",
            "suggested_action": "",
            "reasons": [],
            "timestamp_utc": "",
        },

        "telegram_alerts": [],
        "dispatcher_feedback": [],
        "ratecons": [],
        "events_count": 0,
    }

def apply_feedback_to_case(case_record, feedback_record):
    feedback_type = feedback_record.get("dispatcher_feedback", "")
    document_path = feedback_record.get("document_path", "")

    case_record["updated_at_utc"] = feedback_record.get(
        "timestamp_utc",
        case_record.get("updated_at_utc", ""),
    )

    feedback_item = {
        "timestamp_utc": feedback_record.get("timestamp_utc", ""),
        "feedback": feedback_type,
        "note": feedback_record.get("dispatcher_note", ""),
        "source": feedback_record.get("source", ""),
    }

    case_record["dispatcher_feedback"].append(feedback_item)

    if document_path:
        case_record["ratecons"].append(
            {
                "timestamp_utc": feedback_record.get("timestamp_utc", ""),
                "document_path": document_path,
                "note": feedback_record.get("dispatcher_note", ""),
                "source": feedback_record.get("source", ""),
            }
        )

    status_update = status_update_from_feedback(feedback_type)

    return apply_status_update_to_case(
        case_record=case_record,
        status_update=status_update,
    )

def apply_outbox_to_case(case_record, outbox_record):
    case_record["updated_at_utc"] = outbox_record.get(
        "timestamp_utc",
        case_record.get("updated_at_utc", ""),
    )

    alert_item = {
        "timestamp_utc": outbox_record.get("timestamp_utc", ""),
        "message_type": outbox_record.get("message_type", ""),
        "category": outbox_record.get("category", ""),
        "telegram_message_id": outbox_record.get("telegram_message_id", ""),
        "send_success": outbox_record.get("send_success", False),
        "source": "telegram_outbox",
    }

    case_record["telegram_alerts"].append(alert_item)

    return case_record

def feedback_matches_case(feedback_record, case_record):
    feedback_driver = normalize_text(feedback_record.get("driver_name", ""))
    feedback_load_id = normalize_text(feedback_record.get("load_id", ""))
    feedback_reference_id = normalize_text(feedback_record.get("reference_id", ""))

    case_driver = normalize_text(case_record.get("driver_name", ""))
    case_load_id = normalize_text(case_record.get("load_id", ""))
    case_reference_id = normalize_text(case_record.get("reference_id", ""))

    if feedback_driver and case_driver and feedback_driver != case_driver:
        return False

    if feedback_load_id and feedback_load_id == case_load_id:
        return True

    if feedback_reference_id and feedback_reference_id == case_reference_id:
        return True

    if feedback_load_id and feedback_load_id == case_reference_id:
        return True

    if feedback_reference_id and feedback_reference_id == case_load_id:
        return True

    return False


def outbox_matches_case(outbox_record, case_record):
    outbox_reference_id = normalize_text(outbox_record.get("reference_id", ""))
    outbox_driver = normalize_text(outbox_record.get("driver_name", ""))
    outbox_pickup = normalize_text(outbox_record.get("pickup", ""))
    outbox_delivery = normalize_text(outbox_record.get("delivery", ""))
    outbox_broker_mc = normalize_text(outbox_record.get("broker_mc", ""))

    case_reference_id = normalize_text(case_record.get("reference_id", ""))
    case_driver = normalize_text(case_record.get("driver_name", ""))
    case_pickup = normalize_text(case_record.get("pickup", ""))
    case_delivery = normalize_text(case_record.get("delivery", ""))
    case_broker_mc = normalize_text(case_record.get("broker_mc", ""))

    if outbox_reference_id and outbox_reference_id != "no id":
        if outbox_reference_id == case_reference_id and outbox_driver == case_driver:
            return True

    if (
        outbox_driver
        and outbox_pickup
        and outbox_delivery
        and outbox_driver == case_driver
        and outbox_pickup == case_pickup
        and outbox_delivery == case_delivery
    ):
        if not outbox_broker_mc or not case_broker_mc:
            return True

        if outbox_broker_mc == case_broker_mc:
            return True

    return False


def simulation_event_matches_case(simulation_event, case_record):
    payload = simulation_event.get("payload", {}) or {}

    simulation_load_id = normalize_text(simulation_event.get("load_id", ""))
    event_load = payload.get("load", {}) or {}
    updates = payload.get("updates", {}) or {}

    possible_reference_ids = [
        simulation_load_id,
        normalize_text(event_load.get("reference_id", "")),
        normalize_text(updates.get("reference_id", "")),
    ]

    case_reference_id = normalize_text(case_record.get("reference_id", ""))
    case_load_id = normalize_text(case_record.get("load_id", ""))

    for possible_id in possible_reference_ids:
        if not possible_id:
            continue

        if possible_id == case_reference_id:
            return True

        if possible_id == case_load_id:
            return True

    return False


def build_simulation_payload(simulation_event):
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
            "reference_id": event_load.get("reference_id", simulation_event.get("load_id", "")),
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


def build_cases_and_events(
    decision_records,
    feedback_records,
    telegram_outbox_records=None,
    simulation_event_records=None,
):
    telegram_outbox_records = telegram_outbox_records or []
    simulation_event_records = simulation_event_records or []

    cases_by_id = {}
    events = []

    for decision in decision_records:
        case = build_case_from_decision(decision)
        case_id = case["case_id"]

        # Keep latest decision snapshot for the same case.
        cases_by_id[case_id] = case

        events.append(
            build_ai_decision_created_event(
                case_id=case_id,
                case_record=case,
                decision_record=decision,
            )
        )

    for outbox in telegram_outbox_records:
        if not outbox.get("send_success", False):
            continue

        if outbox.get("message_type") not in [
            "LOAD_OPPORTUNITY",
            "REVIEW_ONCE",
            "MARKET_SNAPSHOT",
            "SEARCH_HEALTH_CHECK",
        ]:
            continue

        matched_case_id = None

        for case_id, case in cases_by_id.items():
            if outbox_matches_case(outbox, case):
                matched_case_id = case_id
                break

        if not matched_case_id:
            case = build_case_from_outbox(outbox)
            matched_case_id = case["case_id"]
            cases_by_id[matched_case_id] = case

        case = cases_by_id[matched_case_id]
        apply_outbox_to_case(case, outbox)

        events.append(
            build_telegram_alert_sent_event(
                case_id=matched_case_id,
                case_record=case,
                outbox_record=outbox,
            )
        )

    if simulation_event_records:
        for simulation_event in simulation_event_records:
            event_type = simulation_event.get("event_type", "")

            if event_type != "LOAD_APPEARED":
                continue

            for case_id, case in cases_by_id.items():
                if not simulation_event_matches_case(simulation_event, case):
                    continue

                events.append(
                    build_load_board_simulation_event(
                        case_id=case_id,
                        case_record=case,
                        simulation_event=simulation_event,
                    )
                )

                break

    for feedback in feedback_records:
        matched_case_id = None

        for case_id, case in cases_by_id.items():
            if feedback_matches_case(feedback, case):
                matched_case_id = case_id
                break

        if not matched_case_id:
            matched_case_id = build_case_id(
                driver_name=feedback.get("driver_name", ""),
                load_id=feedback.get("load_id", ""),
                reference_id=feedback.get("reference_id", ""),
                broker_mc=feedback.get("broker_mc", ""),
            )

            cases_by_id[matched_case_id] = {
                "case_id": matched_case_id,
                "created_at_utc": feedback.get("timestamp_utc", ""),
                "updated_at_utc": feedback.get("timestamp_utc", ""),
                "status": status_update_from_feedback(
                    feedback.get("dispatcher_feedback", "")
                ).get("status", "OPEN"),
                "final_outcome": status_update_from_feedback(
                    feedback.get("dispatcher_feedback", "")
                ).get("final_outcome"),
                "driver_name": safe(feedback.get("driver_name", "")),
                "driver_location": "",
                "driver_equipment": "",
                "load_id": safe(feedback.get("load_id", "")),
                "reference_id": safe(feedback.get("reference_id", "")),
                "pickup": safe(feedback.get("pickup", "")),
                "delivery": safe(feedback.get("delivery", "")),
                "rate": safe(feedback.get("rate", 0)),
                "loaded_miles": 0,
                "empty_miles": 0,
                "total_miles": 0,
                "total_rpm": 0,
                "weight": 0,
                "posted_trailer_type": "",
                "commodity": "",
                "broker_name": safe(feedback.get("broker_name", "")),
                "broker_mc": safe(feedback.get("broker_mc", "")),
                "broker_contact": "",
                "broker_status": "",
                "credit_score": "",
                "days_to_pay": "",
                "ai_decision": {
                    "decision": safe(feedback.get("ai_decision", "")),
                    "category": safe(feedback.get("ai_category", "")),
                    "score": safe(feedback.get("ai_score", 0)),
                    "priority": "",
                    "suggested_action": "",
                    "reasons": feedback.get("ai_reasons", []),
                    "timestamp_utc": "",
                },
                "telegram_alerts": [],
                "dispatcher_feedback": [],
                "ratecons": [],
                "events_count": 0,
            }

        case = cases_by_id[matched_case_id]
        apply_feedback_to_case(case, feedback)

        events.append(
            build_dispatcher_feedback_added_event(
                case_id=matched_case_id,
                case_record=case,
                feedback_record=feedback,
            )
        )

        if feedback.get("document_path"):
            events.append(
                build_ratecon_received_event(
                    case_id=matched_case_id,
                    case_record=case,
                    feedback_record=feedback,
                )
            )

    events = dedupe_dispatch_events(events)

    cases = list(cases_by_id.values())

    events_by_case = {}

    for event in events:
        case_id = event.get("case_id", "")
        events_by_case[case_id] = events_by_case.get(case_id, 0) + 1

    for case in cases:
        case["events_count"] = events_by_case.get(case.get("case_id", ""), 0)

    return cases, events
