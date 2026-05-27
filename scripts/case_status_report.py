import argparse
from asyncio import events
import json
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


def count_by(records, key, default="UNKNOWN"):
    counts = {}

    for record in records:
        value = record.get(key, default)

        if value is None or value == "":
            value = default

        counts[value] = counts.get(value, 0) + 1

    return counts


def count_ai_categories(cases):
    counts = {}

    for case in cases:
        ai_decision = case.get("ai_decision", {}) or {}
        category = ai_decision.get("category", "") or "UNKNOWN"

        counts[category] = counts.get(category, 0) + 1

    return counts


def count_ai_decisions(cases):
    counts = {}

    for case in cases:
        ai_decision = case.get("ai_decision", {}) or {}
        decision = ai_decision.get("decision", "") or "UNKNOWN"

        counts[decision] = counts.get(decision, 0) + 1

    return counts


def events_for_cases(events, cases):
    case_ids = set()

    for case in cases:
        case_id = case.get("case_id", "")

        if case_id:
            case_ids.add(case_id)

    if not case_ids:
        return []

    return [
        event for event in events
        if event.get("case_id", "") in case_ids
    ]


def event_counts(events):
    return count_by(events, "event_type")


def total_telegram_alerts(cases):
    return sum(len(case.get("telegram_alerts", [])) for case in cases)


def total_feedback_items(cases):
    return sum(len(case.get("dispatcher_feedback", [])) for case in cases)


def total_ratecons(cases):
    return sum(len(case.get("ratecons", [])) for case in cases)


def cases_with_telegram(cases):
    return [
        case for case in cases
        if len(case.get("telegram_alerts", [])) > 0
    ]


def cases_with_feedback(cases):
    return [
        case for case in cases
        if len(case.get("dispatcher_feedback", [])) > 0
    ]


def cases_with_ratecons(cases):
    return [
        case for case in cases
        if len(case.get("ratecons", [])) > 0
    ]


def cases_by_status(cases, status):
    return [
        case for case in cases
        if normalize(case.get("status", "")) == normalize(status)
    ]


def case_ai_decision(case):
    ai_decision = case.get("ai_decision", {}) or {}
    return ai_decision.get("decision", "") or "UNKNOWN"


def case_ai_category(case):
    ai_decision = case.get("ai_decision", {}) or {}
    return ai_decision.get("category", "") or "UNKNOWN"


def filter_cases(cases, driver="", status="", category="", decision="", has_feedback=False, has_telegram=False):
    filtered = []

    for case in cases:
        if driver:
            if normalize(case.get("driver_name", "")) != normalize(driver):
                continue

        if status:
            if normalize(case.get("status", "")) != normalize(status):
                continue

        if category:
            if normalize(case_ai_category(case)) != normalize(category):
                continue

        if decision:
            if normalize(case_ai_decision(case)) != normalize(decision):
                continue

        if has_feedback:
            if not case.get("dispatcher_feedback", []):
                continue

        if has_telegram:
            if not case.get("telegram_alerts", []):
                continue

        filtered.append(case)

    return filtered


def sort_cases_latest(cases):
    return sorted(
        cases,
        key=lambda case: case.get("updated_at_utc", "") or case.get("created_at_utc", ""),
        reverse=True,
    )


def print_count_section(title, counts):
    print("")
    print(title)
    print("-" * len(title))

    if not counts:
        print("No data.")
        return

    for key, value in sorted(counts.items(), key=lambda item: (-item[1], str(item[0]))):
        print(f"{key}: {value}")


def short_case_line(case):
    case_id = case.get("case_id", "")
    driver = case.get("driver_name", "")
    status = case.get("status", "")
    category = case_ai_category(case)
    decision = case_ai_decision(case)
    pickup = case.get("pickup", "")
    delivery = case.get("delivery", "")
    rate = case.get("rate", "")
    reference_id = case.get("reference_id", "")
    broker = case.get("broker_name", "")

    telegram_count = len(case.get("telegram_alerts", []))
    feedback_count = len(case.get("dispatcher_feedback", []))
    ratecon_count = len(case.get("ratecons", []))

    return (
        f"{case_id} | {driver} | {status} | {decision}/{category} | "
        f"{pickup} -> {delivery} | ${rate} | REF: {reference_id} | "
        f"{broker} | TG:{telegram_count} FB:{feedback_count} RC:{ratecon_count}"
    )


def print_case_list(title, cases, limit=10):
    print("")
    print(title)
    print("-" * len(title))

    if not cases:
        print("No cases.")
        return

    for case in sort_cases_latest(cases)[:limit]:
        print(short_case_line(case))


def print_replay_examples(cases, limit=5):
    print("")
    print("Replay examples")
    print("---------------")

    example_cases = [
        case for case in sort_cases_latest(cases)
        if case.get("reference_id", "") and case.get("driver_name", "")
    ]

    if not example_cases:
        print("No replay examples available.")
        return

    for case in example_cases[:limit]:
        reference_id = case.get("reference_id", "")
        driver_name = case.get("driver_name", "")

        print(
            f"py scripts/case_replay_report.py {reference_id} {driver_name} --latest"
        )


def print_overview(cases, events):
    print("")
    print("Overview")
    print("--------")
    print(f"Total cases: {len(cases)}")
    print(f"Total events: {len(events)}")
    print(f"Cases with Telegram alerts: {len(cases_with_telegram(cases))}")
    print(f"Total Telegram alerts: {total_telegram_alerts(cases)}")
    print(f"Cases with dispatcher feedback: {len(cases_with_feedback(cases))}")
    print(f"Total feedback items: {total_feedback_items(cases)}")
    print(f"Cases with RateCons: {len(cases_with_ratecons(cases))}")
    print(f"Total RateCons: {total_ratecons(cases)}")


def print_filters(args):
    active_filters = []

    if args.driver:
        active_filters.append(f"driver={args.driver}")

    if args.status:
        active_filters.append(f"status={args.status}")

    if args.category:
        active_filters.append(f"category={args.category}")

    if args.decision:
        active_filters.append(f"decision={args.decision}")

    if args.has_feedback:
        active_filters.append("has_feedback=true")

    if args.has_telegram:
        active_filters.append("has_telegram=true")

    if active_filters:
        print("")
        print("Active filters")
        print("--------------")

        for item in active_filters:
            print(f"- {item}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Show DispatchCase status report."
    )

    parser.add_argument(
        "--driver",
        default="",
        help="Filter by driver name. Example: --driver TestCAFlatbed",
    )

    parser.add_argument(
        "--status",
        default="",
        help="Filter by case status. Example: --status OPEN",
    )

    parser.add_argument(
        "--category",
        default="",
        help='Filter by AI category. Example: --category "RATE CHECK"',
    )

    parser.add_argument(
        "--decision",
        default="",
        help="Filter by AI decision. Example: --decision MATCH",
    )

    parser.add_argument(
        "--has-feedback",
        action="store_true",
        help="Show only cases that have dispatcher feedback.",
    )

    parser.add_argument(
        "--has-telegram",
        action="store_true",
        help="Show only cases that were sent to Telegram.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="How many cases to show in each list.",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show only overview and counts, without case lists.",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    cases = load_jsonl(DISPATCH_CASES_FILE)
    events = load_jsonl(DISPATCH_EVENTS_FILE)

    if not cases:
        print("No dispatch cases found.")
        print("Run first:")
        print("py scripts/build_dispatch_cases.py")
        return

    filtered_cases = filter_cases(
        cases=cases,
        driver=args.driver,
        status=args.status,
        category=args.category,
        decision=args.decision,
        has_feedback=args.has_feedback,
        has_telegram=args.has_telegram,
    )

    print("=" * 80)
    print("DISPATCH CASE STATUS REPORT")
    print("=" * 80)

    print_filters(args)

    print_overview(filtered_cases, events)

    print_count_section(
        "Status Counts",
        count_by(filtered_cases, "status"),
    )

    print_count_section(
        "AI Decision Counts",
        count_ai_decisions(filtered_cases),
    )

    print_count_section(
        "AI Category Counts",
        count_ai_categories(filtered_cases),
    )

    filtered_events = events_for_cases(events, filtered_cases)

    print_count_section(
        "Event Counts",
         event_counts(filtered_events),
    )

    if args.summary:
        print_replay_examples(filtered_cases, limit=5)
        return

    print_case_list(
        "Latest Cases Matching Filters",
        filtered_cases,
        limit=args.limit,
    )

    print_case_list(
        "Latest OPEN Cases",
        cases_by_status(filtered_cases, "OPEN"),
        limit=args.limit,
    )

    print_case_list(
        "Latest COVERED Cases",
        cases_by_status(filtered_cases, "COVERED"),
        limit=args.limit,
    )

    print_case_list(
        "Cases With Feedback",
        cases_with_feedback(filtered_cases),
        limit=args.limit,
    )

    print_replay_examples(filtered_cases, limit=5)


if __name__ == "__main__":
    main()