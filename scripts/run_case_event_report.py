import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.case_event_report import build_case_event_report  # noqa: E402
from tests.fixtures.case_event_records import SYNTHETIC_CASE_EVENT_RECORDS  # noqa: E402


def format_counts(counts):
    if not counts:
        return "none"

    return ", ".join(
        f"{key or 'NO_CASE_ID'}: {value}"
        for key, value in sorted(counts.items())
    )


def main(argv=None):
    _ = argv
    report = build_case_event_report(SYNTHETIC_CASE_EVENT_RECORDS)
    case_ids = [
        case_id
        for case_id in report["counts_by_case_id"]
        if case_id
    ]

    print("CASE EVENT TIMELINE REPORT DRY-RUN")
    print(f"Total events: {report['total_events']}")
    print(f"Counts by type: {format_counts(report['counts_by_event_type'])}")
    print(f"Counts by group: {format_counts(report['counts_by_event_group'])}")
    print(f"Cases found: {len(case_ids)}")
    print(f"Counts by case: {format_counts(report['counts_by_case_id'])}")
    print(
        "Unknown event types: "
        f"{', '.join(report['unknown_event_types']) or 'none'}"
    )
    print("")

    for case_id, events in sorted(report["timeline_by_case_id"].items()):
        print(f"- {case_id or 'NO_CASE_ID'}: {len(events)} events")

        for event in events:
            print(
                f"  {event.get('timestamp_utc', '') or 'NO_TIME'} | "
                f"{event.get('event_type', '') or 'NO_EVENT_TYPE'} | "
                f"{event.get('event_group', '') or 'NO_GROUP'}"
            )

    print("")
    print("DRY RUN ONLY - synthetic event report only")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
