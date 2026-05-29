import json
from app.market_intelligence.case_id_resolver import build_case_id
from app.market_intelligence.case_factory import (
    build_case_from_decision,
    build_case_from_feedback,
    build_case_from_outbox,
)
from app.market_intelligence.case_matcher import (
    feedback_matches_case,
    outbox_matches_case,
    simulation_event_matches_case,
)
from pathlib import Path
from app.market_intelligence.case_event_builder import (
    build_ai_decision_created_event,
    build_dispatcher_feedback_added_event,
    build_load_board_simulation_event,
    build_ratecon_received_event,
    build_telegram_alert_sent_event,
    dedupe_dispatch_events,
)
from app.market_intelligence.case_update_applier import (
    apply_feedback_to_case,
    apply_outbox_to_case,
)


DISPATCH_CASES_FILE = Path("data/dispatch_cases.jsonl")
CASE_ELIGIBLE_OUTBOX_MESSAGE_TYPES = {
    "LOAD_OPPORTUNITY",
    "REVIEW_ONCE",
    "SEARCH_HEALTH_CHECK",
}

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

        if outbox.get("message_type") not in CASE_ELIGIBLE_OUTBOX_MESSAGE_TYPES:
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

            cases_by_id[matched_case_id] = build_case_from_feedback(
                feedback_record=feedback,
                case_id=matched_case_id,
            )

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
