import hashlib
import json
from pathlib import Path

from app.market_intelligence.event_logger import build_dispatch_event


DISPATCH_CASES_FILE = Path("data/dispatch_cases.jsonl")


def stable_hash(text):
    text = str(text or "").strip().lower()
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


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


def normalize_text(value):
    return str(value or "").strip().lower()


def build_case_id(driver_name, load_id, reference_id="", broker_mc=""):
    reference_id = str(reference_id or "").strip()
    load_id = str(load_id or "").strip()
    driver_name = str(driver_name or "").strip()
    broker_mc = str(broker_mc or "").strip()

    if reference_id and reference_id.upper() != "NO ID":
        base = f"{driver_name}|REF:{reference_id}|MC:{broker_mc}"

    elif load_id:
        base = f"{driver_name}|LOAD:{load_id}|MC:{broker_mc}"

    else:
        base = f"{driver_name}|MC:{broker_mc}"

    return f"CASE-{stable_hash(base)}"

def status_update_from_feedback(feedback_type):
    feedback_type = str(feedback_type or "").lower().strip()

    working_status_map = {
        "called_broker": "CALLED",
        "called": "CALLED",
        "sent_to_driver": "SENT_TO_DRIVER",
    }

    final_status_map = {
        "booked": "BOOKED",
        "ratecon": "RATECON_RECEIVED",
        "ratecon_received": "RATECON_RECEIVED",
        "driver_rejected": "REJECTED",
        "rate_too_low": "REJECTED",
        "bad_broker": "REJECTED",
        "wrong_equipment": "REJECTED",
        "weight_issue": "REJECTED",
        "time_issue": "REJECTED",
        "covered": "COVERED",
        "duplicate": "DUPLICATE",
        "skipped": "SKIPPED",
        "not_interested": "SKIPPED",
    }

    if feedback_type in working_status_map:
        return {
            "status": working_status_map[feedback_type],
            "final_outcome": None,
        }

    if feedback_type in final_status_map:
        final_status = final_status_map[feedback_type]

        return {
            "status": final_status,
            "final_outcome": final_status,
        }

    return {
        "status": "OPEN",
        "final_outcome": None,
    }


def status_from_feedback(feedback_type):
    status_update = status_update_from_feedback(feedback_type)

    return status_update.get("status", "OPEN")


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
    new_status = status_update.get("status", "OPEN")
    new_final_outcome = status_update.get("final_outcome")

    current_status = str(case_record.get("status", "") or "").strip()
    current_final_outcome = case_record.get("final_outcome")

    final_statuses = {
        "BOOKED",
        "RATECON_RECEIVED",
        "REJECTED",
        "SKIPPED",
        "COVERED",
        "REMOVED",
        "DUPLICATE",
    }

    working_status_order = {
        "OPEN": 0,
        "CALLED": 1,
        "SENT_TO_DRIVER": 2,
    }

    # Final feedback always wins.
    if new_final_outcome:
        case_record["status"] = new_status
        case_record["final_outcome"] = new_final_outcome
        return case_record

    # If the case already has a final outcome, do not downgrade it
    # with working feedback like called_broker or sent_to_driver.
    if current_final_outcome:
        return case_record

    if current_status in final_statuses:
        return case_record

    # Working statuses can only move forward:
    # OPEN -> CALLED -> SENT_TO_DRIVER
    if new_status != "OPEN":
        current_rank = working_status_order.get(current_status, 0)
        new_rank = working_status_order.get(new_status, 0)

        if new_rank >= current_rank:
            case_record["status"] = new_status

    return case_record

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
            build_dispatch_event(
                case_id=case_id,
                event_type="AI_DECISION_CREATED",
                driver_name=case.get("driver_name", ""),
                load_id=case.get("load_id", ""),
                reference_id=case.get("reference_id", ""),
                timestamp_utc=decision.get("timestamp_utc", ""),
                source="decision_logger",
                payload={
                    "decision": decision.get("decision", ""),
                    "category": decision.get("category", ""),
                    "score": decision.get("score", 0),
                    "reasons": decision.get("reasons", []),
                    "pickup": decision.get("pickup", ""),
                    "delivery": decision.get("delivery", ""),
                    "rate": decision.get("rate", 0),
                },
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
            build_dispatch_event(
                case_id=matched_case_id,
                event_type="TELEGRAM_ALERT_SENT",
                driver_name=case.get("driver_name", ""),
                load_id=case.get("load_id", ""),
                reference_id=case.get("reference_id", ""),
                timestamp_utc=outbox.get("timestamp_utc", ""),
                source="telegram_outbox",
                payload={
                    "message_type": outbox.get("message_type", ""),
                    "category": outbox.get("category", ""),
                    "telegram_message_id": outbox.get("telegram_message_id", ""),
                    "pickup": outbox.get("pickup", ""),
                    "delivery": outbox.get("delivery", ""),
                    "rate": outbox.get("rate", ""),
                    "broker": outbox.get("broker", ""),
                    "broker_mc": outbox.get("broker_mc", ""),
                    "reference_id": outbox.get("reference_id", ""),
                },
            )
        )

        for simulation_event in simulation_event_records:
         event_type = simulation_event.get("event_type", "")

        if event_type not in [
            "LOAD_APPEARED",
            "LOAD_UPDATED",
            "LOAD_REMOVED",
        ]:
            continue

        for case_id, case in cases_by_id.items():
            if not simulation_event_matches_case(simulation_event, case):
                continue

            if event_type == "LOAD_REMOVED":
                removed_reason = str(simulation_event.get("reason", "") or "").strip().lower()

                if removed_reason == "covered":
                    case["status"] = "COVERED"
                    case["final_outcome"] = "COVERED"
                else:
                    case["status"] = "REMOVED"
                    case["final_outcome"] = "REMOVED"

                case["updated_at_utc"] = simulation_event.get(
                    "timestamp_utc",
                    case.get("updated_at_utc", ""),
                )

            if event_type == "LOAD_UPDATED":
                case["updated_at_utc"] = simulation_event.get(
                    "timestamp_utc",
                    case.get("updated_at_utc", ""),
                )

            events.append(
                build_dispatch_event(
                    case_id=case_id,
                    event_type=event_type,
                    driver_name=case.get("driver_name", ""),
                    load_id=case.get("load_id", ""),
                    reference_id=case.get("reference_id", ""),
                    timestamp_utc=simulation_event.get("timestamp_utc", ""),
                    source="load_board_simulation",
                    payload=build_simulation_payload(simulation_event),
                )
            )

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
            build_dispatch_event(
                case_id=matched_case_id,
                event_type="DISPATCHER_FEEDBACK_ADDED",
                driver_name=case.get("driver_name", ""),
                load_id=case.get("load_id", ""),
                reference_id=case.get("reference_id", ""),
                timestamp_utc=feedback.get("timestamp_utc", ""),
                source=feedback.get("source", "dispatcher_feedback"),
                payload={
                    "feedback": feedback.get("dispatcher_feedback", ""),
                    "note": feedback.get("dispatcher_note", ""),
                    "document_path": feedback.get("document_path", ""),
                },
            )
        )

        if feedback.get("document_path"):
            events.append(
                build_dispatch_event(
                    case_id=matched_case_id,
                    event_type="RATECON_RECEIVED",
                    driver_name=case.get("driver_name", ""),
                    load_id=case.get("load_id", ""),
                    reference_id=case.get("reference_id", ""),
                    timestamp_utc=feedback.get("timestamp_utc", ""),
                    source=feedback.get("source", "telegram_document"),
                    payload={
                        "document_path": feedback.get("document_path", ""),
                        "note": feedback.get("dispatcher_note", ""),
                    },
                )
            )

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

    events = deduped_events

    cases = list(cases_by_id.values())

    events_by_case = {}

    for event in events:
        case_id = event.get("case_id", "")
        events_by_case[case_id] = events_by_case.get(case_id, 0) + 1

    for case in cases:
        case["events_count"] = events_by_case.get(case.get("case_id", ""), 0)

    return cases, events
