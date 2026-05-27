import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.dispatch_case import (
    DISPATCH_CASES_FILE,
    build_cases_and_events,
    load_jsonl,
    write_jsonl,
)
from app.market_intelligence.event_logger import DISPATCH_EVENTS_FILE


DECISION_HISTORY_FILE = Path("data/decision_history.jsonl")
DISPATCHER_FEEDBACK_FILE = Path("data/dispatcher_feedback.jsonl")


def main():
    decision_records = load_jsonl(DECISION_HISTORY_FILE)
    feedback_records = load_jsonl(DISPATCHER_FEEDBACK_FILE)

    print(f"Decision records found: {len(decision_records)}")
    print(f"Feedback records found: {len(feedback_records)}")

    if not decision_records and not feedback_records:
        print("No decisions or feedback found.")
        print("Run first:")
        print("py scripts/log_decisions_snapshot.py")
        return

    cases, events = build_cases_and_events(
        decision_records=decision_records,
        feedback_records=feedback_records,
    )

    write_jsonl(DISPATCH_CASES_FILE, cases)
    write_jsonl(DISPATCH_EVENTS_FILE, events)

    status_counts = {}

    for case in cases:
        status = case.get("status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1

    print("")
    print("Dispatch cases built.")
    print(f"Cases: {len(cases)}")
    print(f"Events: {len(events)}")
    print("")
    print("Status counts:")

    for status, count in sorted(status_counts.items()):
        print(f"- {status}: {count}")

    print("")
    print("Saved to:")
    print(f"- {DISPATCH_CASES_FILE}")
    print(f"- {DISPATCH_EVENTS_FILE}")


if __name__ == "__main__":
    main()