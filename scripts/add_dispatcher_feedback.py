import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DECISION_HISTORY_FILE = Path("data/decision_history.jsonl")
DISPATCHER_FEEDBACK_FILE = Path("data/dispatcher_feedback.jsonl")


ALLOWED_FEEDBACK_TYPES = [
    "booked",
    "skipped",
    "called_broker",
    "sent_to_driver",
    "driver_rejected",
    "rate_too_low",
    "bad_broker",
    "wrong_equipment",
    "weight_issue",
    "time_issue",
    "covered",
    "duplicate",
    "good_option",
    "not_interested",
    "other",
]


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


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


def append_jsonl(file_path, record):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def find_recent_decision(load_id):
    records = load_jsonl(DECISION_HISTORY_FILE)

    load_id = str(load_id or "").strip().lower()

    if not load_id:
        return None

    # Search newest first.
    for record in reversed(records):
        record_load_id = str(record.get("load_id", "") or "").strip().lower()
        reference_id = str(record.get("reference_id", "") or "").strip().lower()

        if record_load_id == load_id:
            return record

        if reference_id and reference_id == load_id:
            return record

    return None


def print_usage():
    print("Usage:")
    print(
        "py scripts/add_dispatcher_feedback.py <load_id_or_reference_id> "
        "<feedback_type> \"optional note\""
    )
    print("")
    print("Allowed feedback types:")
    for feedback_type in ALLOWED_FEEDBACK_TYPES:
        print(f"- {feedback_type}")
    print("")
    print("Examples:")
    print(
        'py scripts/add_dispatcher_feedback.py MANUAL-RATECHECK-001 booked '
        '"Broker gave $4200, booked"'
    )
    print(
        'py scripts/add_dispatcher_feedback.py 3010980 driver_rejected '
        '"Driver does not want permit load"'
    )


def main():
    if len(sys.argv) < 3:
        print_usage()
        return

    load_id = sys.argv[1].strip()
    feedback_type = sys.argv[2].strip().lower()
    note = ""

    if len(sys.argv) >= 4:
        note = " ".join(sys.argv[3:]).strip()

    if feedback_type not in ALLOWED_FEEDBACK_TYPES:
        print(f"Unknown feedback type: {feedback_type}")
        print("")
        print_usage()
        return

    matched_decision = find_recent_decision(load_id)

    if not matched_decision:
        print(f"No matching decision found for: {load_id}")
        print("")
        print("Tip:")
        print("- First run: py scripts/log_decisions_snapshot.py")
        print("- Then use load_id or reference_id from decision history.")
        return

    feedback_record = {
        "timestamp_utc": utc_now_iso(),
        "load_id": matched_decision.get("load_id", ""),
        "reference_id": matched_decision.get("reference_id", ""),
        "driver_name": matched_decision.get("driver_name", ""),
        "pickup": matched_decision.get("pickup", ""),
        "delivery": matched_decision.get("delivery", ""),
        "rate": matched_decision.get("rate", 0),
        "broker_name": matched_decision.get("broker_name", ""),
        "broker_mc": matched_decision.get("broker_mc", ""),
        "ai_decision": matched_decision.get("decision", ""),
        "ai_category": matched_decision.get("category", ""),
        "ai_score": matched_decision.get("score", 0),
        "ai_reasons": matched_decision.get("reasons", []),
        "dispatcher_feedback": feedback_type,
        "dispatcher_note": note,
        "source": "manual_cli",
    }

    append_jsonl(DISPATCHER_FEEDBACK_FILE, feedback_record)

    print("Dispatcher feedback saved.")
    print("")
    print(f"Driver: {feedback_record['driver_name']}")
    print(f"Load: {feedback_record['pickup']} -> {feedback_record['delivery']}")
    print(f"Reference ID: {feedback_record['reference_id'] or 'NO ID'}")
    print(f"AI decision: {feedback_record['ai_decision']}")
    print(f"AI category: {feedback_record['ai_category']}")
    print(f"Feedback: {feedback_record['dispatcher_feedback']}")

    if note:
        print(f"Note: {note}")

    print("")
    print(f"Saved to: {DISPATCHER_FEEDBACK_FILE}")


if __name__ == "__main__":
    main()
