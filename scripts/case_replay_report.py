import json
import sys
from pathlib import Path


DISPATCH_CASES_FILE = Path("data/dispatch_cases.jsonl")
DISPATCH_EVENTS_FILE = Path("data/dispatch_events.jsonl")


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


def normalize(value):
    return str(value or "").strip().lower()


def case_values(case):
    return [
        case.get("case_id", ""),
        case.get("load_id", ""),
        case.get("reference_id", ""),
        case.get("pickup", ""),
        case.get("delivery", ""),
        case.get("broker_mc", ""),
    ]


def case_matches_search(case, search_value):
    search_value_normalized = normalize(search_value)

    if not search_value_normalized:
        return False

    for value in case_values(case):
        if normalize(value) == search_value_normalized:
            return True

    combined_text = " ".join(
        [
            str(case.get("case_id", "")),
            str(case.get("load_id", "")),
            str(case.get("reference_id", "")),
            str(case.get("pickup", "")),
            str(case.get("delivery", "")),
            str(case.get("broker_name", "")),
            str(case.get("broker_mc", "")),
        ]
    ).lower()

    return search_value_normalized in combined_text


def find_matching_cases(search_value, cases, driver_filter=""):
    driver_filter_normalized = normalize(driver_filter)

    matches = []

    for case in cases:
        if not case_matches_search(case, search_value):
            continue

        if driver_filter_normalized:
            if normalize(case.get("driver_name", "")) != driver_filter_normalized:
                continue

        matches.append(case)

    return matches


def case_sort_score(case):
    score = 0

    ai_decision = case.get("ai_decision", {}) or {}

    if case.get("telegram_alerts"):
        score += 100

    if case.get("dispatcher_feedback"):
        score += 50

    if case.get("ratecons"):
        score += 50

    if ai_decision.get("decision") == "MATCH":
        score += 30

    if ai_decision.get("decision") == "REVIEW_ONCE":
        score += 20

    if case.get("status") != "OPEN":
        score += 10

    return score


def pick_best_case(matches):
    if not matches:
        return None

    sorted_matches = sorted(
        matches,
        key=case_sort_score,
        reverse=True,
    )

    return sorted_matches[0]


def print_case_candidates(matches):
    print("")
    print("Multiple cases found for this search.")
    print("Use driver name as second argument to open the exact case.")
    print("")
    print("Candidates:")

    for case in matches:
        ai_decision = case.get("ai_decision", {}) or {}

        print("")
        print(f"- Case ID: {case.get('case_id', '')}")
        print(f"  Driver: {case.get('driver_name', '')}")
        print(f"  Lane: {case.get('pickup', '')} -> {case.get('delivery', '')}")
        print(f"  Reference ID: {case.get('reference_id', '')}")
        print(f"  Status: {case.get('status', '')}")
        print(f"  AI Decision: {ai_decision.get('decision', '')}")
        print(f"  AI Category: {ai_decision.get('category', '')}")
        print(f"  Telegram alerts: {len(case.get('telegram_alerts', []))}")
        print(f"  Feedback items: {len(case.get('dispatcher_feedback', []))}")

    print("")
    print("Example:")
    print("py scripts/case_replay_report.py SIM-CLEAN-001 TestCAFlatbed")


def events_for_case(case_id, events):
    matching_events = [
        event for event in events
        if event.get("case_id", "") == case_id
    ]

    return sorted(
        matching_events,
        key=lambda event: event.get("timestamp_utc", ""),
    )

def latest_event_window(events):
    if not events:
        return []

    telegram_events = [
        event for event in events
        if event.get("event_type", "") == "TELEGRAM_ALERT_SENT"
    ]

    if not telegram_events:
        return [events[-1]]

    latest_telegram_event = telegram_events[-1]
    latest_telegram_time = latest_telegram_event.get("timestamp_utc", "")

    latest_load_appeared = None
    latest_load_updated = None
    latest_ai_before_telegram = None

    for event in events:
        event_type = event.get("event_type", "")
        event_time = event.get("timestamp_utc", "")

        if event_type == "LOAD_APPEARED":
            latest_load_appeared = event

        if event_type == "LOAD_UPDATED":
            latest_load_updated = event

        if event_type == "AI_DECISION_CREATED" and event_time <= latest_telegram_time:
            latest_ai_before_telegram = event

    latest_events = []

    if latest_load_appeared:
        latest_events.append(latest_load_appeared)

    if latest_load_updated:
        latest_events.append(latest_load_updated)

    if latest_ai_before_telegram:
        latest_events.append(latest_ai_before_telegram)

    latest_events.append(latest_telegram_event)

    for event in events:
        event_time = event.get("timestamp_utc", "")
        event_type = event.get("event_type", "")

        if event_time <= latest_telegram_time:
            continue

        if event_type in [
            "DISPATCHER_FEEDBACK_ADDED",
            "RATECON_RECEIVED",
            "LOAD_REMOVED",
            "BOOKED",
            "COVERED",
        ]:
            latest_events.append(event)

    return latest_events


def print_case_summary(case):
    ai_decision = case.get("ai_decision", {}) or {}

    print("")
    print("=" * 80)
    print("DISPATCH CASE REPLAY")
    print("=" * 80)
    print("")
    print(f"Case ID: {case.get('case_id', '')}")
    print(f"Status: {case.get('status', '')}")
    print(f"Final Outcome: {case.get('final_outcome', '')}")
    print("")
    print(f"Driver: {case.get('driver_name', '')}")
    print(f"Driver Location: {case.get('driver_location', '')}")
    print(f"Driver Equipment: {case.get('driver_equipment', '')}")
    print("")
    print(f"Load ID: {case.get('load_id', '')}")
    print(f"Reference ID: {case.get('reference_id', '')}")
    print(f"Lane: {case.get('pickup', '')} -> {case.get('delivery', '')}")
    print(f"Rate: ${case.get('rate', '')}")
    print(f"Loaded miles: {case.get('loaded_miles', '')}")
    print(f"Empty miles: {case.get('empty_miles', '')}")
    print(f"Total miles: {case.get('total_miles', '')}")
    print(f"Total RPM: ${case.get('total_rpm', '')}")
    print(f"Weight: {case.get('weight', '')}")
    print(f"Trailer: {case.get('posted_trailer_type', '')}")
    print("")
    print(f"Broker: {case.get('broker_name', '')}")
    print(f"MC: {case.get('broker_mc', '')}")
    print(f"Broker Contact: {case.get('broker_contact', '')}")
    print(f"Broker Status: {case.get('broker_status', '')}")
    print("")
    print("AI Decision:")
    print(f"- Decision: {ai_decision.get('decision', '')}")
    print(f"- Category: {ai_decision.get('category', '')}")
    print(f"- Score: {ai_decision.get('score', '')}")
    print(f"- Priority: {ai_decision.get('priority', '')}")
    print(f"- Suggested Action: {ai_decision.get('suggested_action', '')}")

    reasons = ai_decision.get("reasons", [])

    if reasons:
        print("- Reasons:")

        for reason in reasons:
            print(f"  - {reason}")

    print("")
    print(f"Telegram alerts: {len(case.get('telegram_alerts', []))}")
    print(f"Dispatcher feedback items: {len(case.get('dispatcher_feedback', []))}")
    print(f"RateCons: {len(case.get('ratecons', []))}")
    print(f"Events count: {case.get('events_count', 0)}")


def print_timeline(events):
    print("")
    print("=" * 80)
    print("EVENT TIMELINE")
    print("=" * 80)

    if not events:
        print("No events found for this case.")
        return

    for index, event in enumerate(events, start=1):
        payload = event.get("payload", {}) or {}

        print("")
        print(f"{index}. {event.get('event_type', '')}")
        print(f"   Time: {event.get('timestamp_utc', '')}")
        print(f"   Source: {event.get('source', '')}")

        event_type = event.get("event_type", "")

        if event_type == "AI_DECISION_CREATED":
            print(f"   Decision: {payload.get('decision', '')}")
            print(f"   Category: {payload.get('category', '')}")
            print(f"   Score: {payload.get('score', '')}")
            print(f"   Lane: {payload.get('pickup', '')} -> {payload.get('delivery', '')}")
            print(f"   Rate: ${payload.get('rate', '')}")

            reasons = payload.get("reasons", [])

            if reasons:
                print("   Reasons:")

                for reason in reasons:
                    print(f"   - {reason}")

        elif event_type == "TELEGRAM_ALERT_SENT":
            print(f"   Message Type: {payload.get('message_type', '')}")
            print(f"   Category: {payload.get('category', '')}")
            print(f"   Telegram Message ID: {payload.get('telegram_message_id', '')}")
            print(f"   Lane: {payload.get('pickup', '')} -> {payload.get('delivery', '')}")
            print(f"   Rate: ${payload.get('rate', '')}")
            print(f"   Broker: {payload.get('broker', '')}")
            print(f"   MC: {payload.get('broker_mc', '')}")
            print(f"   Reference ID: {payload.get('reference_id', '')}")

        elif event_type == "DISPATCHER_FEEDBACK_ADDED":
            print(f"   Feedback: {payload.get('feedback', '')}")
            print(f"   Note: {payload.get('note', '')}")

            if payload.get("document_path", ""):
                print(f"   Document: {payload.get('document_path', '')}")

        elif event_type == "LOAD_APPEARED":
            print(f"   Simulation Step: {payload.get('simulation_step', '')}")
            print(f"   Event Time: {payload.get('event_time', '')}")
            print(f"   Simulation Load ID: {payload.get('simulation_load_id', '')}")
            print(f"   Lane: {payload.get('pickup', '')} -> {payload.get('delivery', '')}")
            print(f"   Rate: ${payload.get('rate', '')}")
            print(f"   Broker: {payload.get('broker', '')}")
            print(f"   MC: {payload.get('broker_mc', '')}")
            print(f"   Reference ID: {payload.get('reference_id', '')}")

        elif event_type == "LOAD_UPDATED":
            print(f"   Simulation Step: {payload.get('simulation_step', '')}")
            print(f"   Event Time: {payload.get('event_time', '')}")
            print(f"   Simulation Load ID: {payload.get('simulation_load_id', '')}")
            print(f"   Updates: {json.dumps(payload.get('updates', {}), ensure_ascii=False)}")

        elif event_type == "LOAD_REMOVED":
            print(f"   Simulation Step: {payload.get('simulation_step', '')}")
            print(f"   Event Time: {payload.get('event_time', '')}")
            print(f"   Simulation Load ID: {payload.get('simulation_load_id', '')}")
            print(f"   Reason: {payload.get('reason', '')}")

        elif event_type == "RATECON_RECEIVED":
            print(f"   Document: {payload.get('document_path', '')}")
            print(f"   Note: {payload.get('note', '')}")

        else:
            print(f"   Payload: {json.dumps(payload, ensure_ascii=False)}")


def print_usage():
    print("Usage:")
    print("py scripts/case_replay_report.py <case_id_or_reference_id_or_load_id> [driver_name] [--latest]")
    print("")
    print("Examples:")
    print("py scripts/case_replay_report.py SIM-CLEAN-001")
    print("py scripts/case_replay_report.py SIM-CLEAN-001 TestCAFlatbed")
    print("py scripts/case_replay_report.py SIM-CLEAN-001 TestCAFlatbed --latest")
    print("py scripts/case_replay_report.py MANUAL-CLEAN-FLATBED-001 TestCAFlatbed")
    print("py scripts/case_replay_report.py 5617793 TestCAFlatbed")


def main():
    if len(sys.argv) < 2:
        print_usage()
        return

    args = sys.argv[1:]

    latest_only = False

    if "--latest" in args:
        latest_only = True
        args.remove("--latest")

    search_value = args[0]
    driver_filter = ""

    if len(args) >= 2:
        driver_filter = args[1]

    cases = load_jsonl(DISPATCH_CASES_FILE)
    events = load_jsonl(DISPATCH_EVENTS_FILE)

    if not cases:
        print("No dispatch cases found.")
        print("Run first:")
        print("py scripts/build_dispatch_cases.py")
        return

    matches = find_matching_cases(
        search_value=search_value,
        cases=cases,
        driver_filter=driver_filter,
    )

    if not matches:
        print(f"No case found for: {search_value}")

        if driver_filter:
            print(f"Driver filter: {driver_filter}")

        print("")
        print("Tip:")
        print("Try one of these identifiers:")
        print("- case_id")
        print("- load_id")
        print("- reference_id")
        print("- broker MC")
        return

    if len(matches) > 1 and not driver_filter:
        print_case_candidates(matches)
        case = pick_best_case(matches)

        print("")
        print("Opening best match automatically:")
        print(f"Driver: {case.get('driver_name', '')}")
        print(f"Case ID: {case.get('case_id', '')}")

    else:
        case = pick_best_case(matches)

    case_events = events_for_case(case.get("case_id", ""), events)

    if latest_only:
        case_events = latest_event_window(case_events)

    print_case_summary(case)

    if latest_only:
        print("")
        print("Replay mode: latest event window only")

    print_timeline(case_events)


if __name__ == "__main__":
    main()
